import sys
import types
from types import SimpleNamespace
from uuid import uuid4

import pytest

from models.groups import GroupStatus
from repository.friend_repository import FriendRepository

# The friend route imports auth dependencies through the app stack. Those
# modules are optional in this test container, so stub the google auth module
# tree before importing the route module.
google_module = types.ModuleType("google")
google_auth_module = types.ModuleType("google.auth")
google_auth_transport_module = types.ModuleType("google.auth.transport")
google_auth_requests_module = types.ModuleType("google.auth.transport.requests")
google_oauth2_module = types.ModuleType("google.oauth2")
google_id_token_module = types.ModuleType("google.oauth2.id_token")

google_auth_transport_module.requests = google_auth_requests_module
google_oauth2_module.id_token = google_id_token_module
google_module.auth = google_auth_module
google_module.oauth2 = google_oauth2_module

sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.auth", google_auth_module)
sys.modules.setdefault("google.auth.transport", google_auth_transport_module)
sys.modules.setdefault("google.auth.transport.requests", google_auth_requests_module)
sys.modules.setdefault("google.oauth2", google_oauth2_module)
sys.modules.setdefault("google.oauth2.id_token", google_id_token_module)

from routes.friends import create_friend_request


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value


class _FakeSession:
    def __init__(self):
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _FakeResult(None)


@pytest.mark.asyncio
async def test_create_friend_request_uses_enum_status_message(monkeypatch):
    pending_group = SimpleNamespace(
        id=uuid4(),
        status=GroupStatus.PENDING,
    )
    active_group = SimpleNamespace(
        id=uuid4(),
        status=GroupStatus.ACTIVE,
    )

    async def fake_send_friend_request(*args, **kwargs):
        return pending_group

    monkeypatch.setattr("routes.friends.send_friend_request", fake_send_friend_request)

    pending_response = await create_friend_request(
        friend_data=SimpleNamespace(user_code="ABC123"),
        user=SimpleNamespace(id=uuid4()),
        db=SimpleNamespace(),
    )

    assert pending_response.message == "Friend request sent"
    assert pending_response.data["status"] == "PENDING"

    async def fake_send_friend_request_active(*args, **kwargs):
        return active_group

    monkeypatch.setattr(
        "routes.friends.send_friend_request", fake_send_friend_request_active
    )

    active_response = await create_friend_request(
        friend_data=SimpleNamespace(user_code="XYZ789"),
        user=SimpleNamespace(id=uuid4()),
        db=SimpleNamespace(),
    )

    assert active_response.message == "Friend added successfully"
    assert active_response.data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_find_friend_group_between_users_joins_members_on_group_id():
    session = _FakeSession()
    repository = FriendRepository(session)  # type: ignore[arg-type]

    await repository.find_friend_group_between_users(uuid4(), uuid4())

    compiled_sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))

    assert "JOIN group_members ON groups.id = group_members.group_id" in compiled_sql
    assert "group_members.user_id" in compiled_sql
