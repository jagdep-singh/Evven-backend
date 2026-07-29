from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import services.auth_service as auth_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeRefreshTokenRepository:
    def __init__(self, rows: dict):
        self.rows = rows
        self.family_revocations = 0

    async def create(self, **kwargs):
        row = SimpleNamespace(
            id=kwargs["token_id"],
            user_id=kwargs["user_id"],
            token_hash=kwargs["token_hash"],
            family_id=kwargs["family_id"],
            expires_at=kwargs["expires_at"],
            revoked_at=None,
        )
        self.rows[row.id] = row
        return row

    async def get_by_id(self, token_id):
        return self.rows.get(token_id)

    async def revoke(self, token, revoked_at):
        token.revoked_at = revoked_at

    async def rotate(
        self,
        *,
        current_token,
        new_token_id,
        new_token_hash,
        new_expires_at,
        revoked_at,
    ):
        current_token.revoked_at = revoked_at
        row = SimpleNamespace(
            id=new_token_id,
            user_id=current_token.user_id,
            token_hash=new_token_hash,
            family_id=current_token.family_id,
            expires_at=new_expires_at,
            revoked_at=None,
        )
        self.rows[row.id] = row
        return row

    async def revoke_family(self, family_id, revoked_at):
        self.family_revocations += 1
        for row in self.rows.values():
            if row.family_id == family_id:
                row.revoked_at = revoked_at

    async def delete_expired_before(self, cutoff):
        expired_ids = [
            token_id for token_id, row in self.rows.items() if row.expires_at < cutoff
        ]
        for token_id in expired_ids:
            del self.rows[token_id]


class FakeUserRepository:
    def __init__(self, user):
        self.user = user

    async def get_user_by_id(self, user_id):
        if self.user and self.user.id == user_id:
            return self.user
        return None


def make_user():
    return SimpleNamespace(id=uuid4())


def make_refresh_row(user, *, family_id=None, expires_delta=timedelta(days=1)):
    token_id = uuid4()
    raw_token = auth_service.create_refresh_token_with_claims(
        user_id=user.id,
        token_id=token_id,
        expires_at=auth_service.utc_now() + expires_delta,
    )
    row = SimpleNamespace(
        id=token_id,
        user_id=user.id,
        token_hash=auth_service.hash_refresh_token(raw_token),
        family_id=family_id or token_id,
        expires_at=auth_service.utc_now() + expires_delta,
        revoked_at=None,
    )
    return row, raw_token


def install_fakes(monkeypatch, user, rows):
    refresh_repo = FakeRefreshTokenRepository(rows)
    user_repo = FakeUserRepository(user)
    monkeypatch.setattr(auth_service, "RefreshTokenRepository", lambda db: refresh_repo)
    monkeypatch.setattr(auth_service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(auth_service.random, "random", lambda: 1.0)
    return refresh_repo


async def assert_rejected(coro):
    with pytest.raises(HTTPException) as exc:
        await coro
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_normal_rotation_succeeds_and_revokes_old_jti(monkeypatch):
    user = make_user()
    old_row, old_raw = make_refresh_row(user)
    rows = {old_row.id: old_row}
    install_fakes(monkeypatch, user, rows)

    response = await auth_service.rotate_refresh_token(old_raw, db=None)
    new_payload = auth_service.decode_token(response.refresh_token, expected_type="refresh")
    new_id = UUID(new_payload["jti"])

    assert old_row.revoked_at is not None
    assert new_id != old_row.id
    assert rows[new_id].family_id == old_row.family_id
    assert response.access_token


@pytest.mark.anyio
async def test_reusing_rotated_jti_revokes_family_and_current_is_rejected(monkeypatch):
    user = make_user()
    old_row, old_raw = make_refresh_row(user)
    rows = {old_row.id: old_row}
    repo = install_fakes(monkeypatch, user, rows)

    first_response = await auth_service.rotate_refresh_token(old_raw, db=None)
    current_raw = first_response.refresh_token
    current_id = UUID(
        auth_service.decode_token(current_raw, expected_type="refresh")["jti"]
    )

    await assert_rejected(auth_service.rotate_refresh_token(old_raw, db=None))

    assert repo.family_revocations == 1
    assert old_row.revoked_at is not None
    assert rows[current_id].revoked_at is not None

    await assert_rejected(auth_service.rotate_refresh_token(current_raw, db=None))


@pytest.mark.anyio
async def test_expired_unused_row_rejects_without_revoking_siblings(monkeypatch):
    user = make_user()
    family_id = uuid4()
    expired_row, expired_raw = make_refresh_row(
        user, family_id=family_id, expires_delta=timedelta(seconds=-1)
    )
    sibling_row, _ = make_refresh_row(user, family_id=family_id)
    rows = {expired_row.id: expired_row, sibling_row.id: sibling_row}
    repo = install_fakes(monkeypatch, user, rows)

    await assert_rejected(auth_service.rotate_refresh_token(expired_raw, db=None))

    assert repo.family_revocations == 0
    assert expired_row.revoked_at is None
    assert sibling_row.revoked_at is None


@pytest.mark.anyio
async def test_logout_revokes_only_current_session_row(monkeypatch):
    user = make_user()
    family_id = uuid4()
    old_row, _ = make_refresh_row(user, family_id=family_id)
    current_row, current_raw = make_refresh_row(user, family_id=family_id)
    sibling_row, _ = make_refresh_row(user, family_id=family_id)
    old_row.revoked_at = auth_service.utc_now()
    rows = {
        old_row.id: old_row,
        current_row.id: current_row,
        sibling_row.id: sibling_row,
    }
    repo = install_fakes(monkeypatch, user, rows)

    await auth_service.revoke_refresh_token(current_raw, db=None, user_id=user.id)

    assert repo.family_revocations == 0
    assert old_row.revoked_at is not None
    assert current_row.revoked_at is not None
    assert sibling_row.revoked_at is None


@pytest.mark.anyio
async def test_logout_rejects_refresh_token_for_different_user(monkeypatch):
    user = make_user()
    other_user = make_user()
    row, raw = make_refresh_row(user)
    rows = {row.id: row}
    install_fakes(monkeypatch, user, rows)

    await assert_rejected(
        auth_service.revoke_refresh_token(raw, db=None, user_id=other_user.id)
    )

    assert row.revoked_at is None


@pytest.mark.anyio
async def test_logout_rejects_hash_mismatched_refresh_token(monkeypatch):
    user = make_user()
    row, original_raw = make_refresh_row(user)
    tampered_raw = auth_service.create_refresh_token(
        {"sub": str(user.id), "jti": str(row.id), "nonce": "tampered"}
    )
    assert tampered_raw != original_raw
    rows = {row.id: row}
    install_fakes(monkeypatch, user, rows)

    await assert_rejected(
        auth_service.revoke_refresh_token(tampered_raw, db=None, user_id=user.id)
    )

    assert row.revoked_at is None


@pytest.mark.anyio
async def test_hash_mismatch_rejects_matching_jti_with_different_raw_token(monkeypatch):
    user = make_user()
    row, original_raw = make_refresh_row(user)
    tampered_raw = auth_service.create_refresh_token(
        {"sub": str(user.id), "jti": str(row.id), "nonce": "tampered"}
    )
    assert tampered_raw != original_raw
    rows = {row.id: row}
    install_fakes(monkeypatch, user, rows)

    await assert_rejected(auth_service.rotate_refresh_token(tampered_raw, db=None))

    assert row.revoked_at is None
