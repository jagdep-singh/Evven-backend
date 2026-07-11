from types import SimpleNamespace

from services.group_service import _member_response_data


def test_member_response_includes_user_code():
    member = SimpleNamespace(
        id="member-id",
        user=SimpleNamespace(name="Jane", user_code="ABC123"),
        group_id="group-id",
        user_id="user-id",
        joined_at="2024-01-01T00:00:00",
    )

    data = _member_response_data(member)

    assert data["user_code"] == "ABC123"
