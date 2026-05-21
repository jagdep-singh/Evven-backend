from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from main import app
from models.expense_splits import ExpenseSplit
from models.group_expenses import GroupExpense


def auth_headers(user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {user['token']}"}


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


async def register_user(client: AsyncClient, name: str, email: str) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "test123",
        },
    )

    assert response.status_code == 201, response.text

    body = response.json()
    return {
        "id": body["user"]["id"],
        "code": body["user"]["user_code"],
        "name": name,
        "token": body["tokens"]["access_token"],
    }


async def fetch_splits_by_expense(
    expense_ids: list[str],
) -> dict[str, dict[str, Decimal]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                ExpenseSplit.expense_id,
                ExpenseSplit.user_id,
                ExpenseSplit.amount,
            ).where(
                ExpenseSplit.expense_id.in_(
                    [UUID(expense_id) for expense_id in expense_ids]
                )
            )
        )

    splits: dict[str, dict[str, Decimal]] = {}
    for expense_id, user_id, amount in result.all():
        splits.setdefault(str(expense_id), {})[str(user_id)] = money(amount)

    return splits


async def count_group_expenses_and_splits(group_id: str) -> tuple[int, int]:
    group_uuid = UUID(group_id)

    async with AsyncSessionLocal() as session:
        expense_count = await session.scalar(
            select(func.count(GroupExpense.id)).where(
                GroupExpense.group_id == group_uuid
            )
        )
        split_count = await session.scalar(
            select(func.count(ExpenseSplit.id))
            .join(GroupExpense, ExpenseSplit.expense_id == GroupExpense.id)
            .where(GroupExpense.group_id == group_uuid)
        )

    return int(expense_count or 0), int(split_count or 0)


@pytest.mark.anyio
async def test_full_group_expense_flow_covers_all_split_types_and_access_leaks():
    """End-to-end group flow with 5 members, all split types, and leak checks."""
    unique_suffix = uuid4().hex
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport, base_url="https://evenup-backend.onrender.com/"
    ) as client:
        members = [
            await register_user(
                client, name, f"{name.lower()}-{unique_suffix}@test.com"
            )
            for name in ["Jagdeep", "Rohit", "Priya", "Ankur", "Sneha"]
        ]
        outsider = await register_user(
            client,
            "Nisha",
            f"nisha-outsider-{unique_suffix}@test.com",
        )

        creator = members[0]
        creator_headers = auth_headers(creator)

        create_group_response = await client.post(
            "/groups/",
            json={"name": f"Goa Trip {unique_suffix}"},
            headers=creator_headers,
        )
        assert create_group_response.status_code == 201, create_group_response.text
        group_id = create_group_response.json()["data"]["id"]

        for member in members[1:]:
            response = await client.post(
                f"/groups/{group_id}/members",
                json={"user_code": member["code"]},
                headers=creator_headers,
            )
            assert response.status_code == 200, response.text

        list_members_response = await client.get(
            f"/groups/{group_id}/members",
            headers=creator_headers,
        )
        assert list_members_response.status_code == 200, list_members_response.text
        listed_members = list_members_response.json()["data"]
        assert {item["user_id"] for item in listed_members} == {
            member["id"] for member in members
        }

        leak_response = await client.get(
            f"/groups/{group_id}/expenses",
            headers=auth_headers(outsider),
        )
        assert leak_response.status_code == 403, leak_response.text

        expenses_to_create = [
            {
                "title": "Hotel Booking - Equal All",
                "payer": members[0],
                "payload": {
                    "title": "Hotel Booking - Equal All",
                    "amount": "5000.00",
                    "split_type": "equal",
                    "equal_member_ids": [member["id"] for member in members],
                },
                "expected_splits": {
                    member["id"]: Decimal("1000.00") for member in members
                },
            },
            {
                "title": "Beach Shack - Equal Subset",
                "payer": members[1],
                "payload": {
                    "title": "Beach Shack - Equal Subset",
                    "amount": "2400.00",
                    "split_type": "equal",
                    "equal_member_ids": [member["id"] for member in members[:4]],
                },
                "expected_splits": {
                    members[0]["id"]: Decimal("600.00"),
                    members[1]["id"]: Decimal("600.00"),
                    members[2]["id"]: Decimal("600.00"),
                    members[3]["id"]: Decimal("600.00"),
                },
            },
            {
                "title": "Flights - Exact Uneven",
                "payer": members[2],
                "payload": {
                    "title": "Flights - Exact Uneven",
                    "amount": "7135.75",
                    "split_type": "exact",
                    "splits_input": {
                        members[0]["id"]: "1500.25",
                        members[1]["id"]: "1250.50",
                        members[2]["id"]: "1800.00",
                        members[3]["id"]: "2085.00",
                        members[4]["id"]: "500.00",
                    },
                },
                "expected_splits": {
                    members[0]["id"]: Decimal("1500.25"),
                    members[1]["id"]: Decimal("1250.50"),
                    members[2]["id"]: Decimal("1800.00"),
                    members[3]["id"]: Decimal("2085.00"),
                    members[4]["id"]: Decimal("500.00"),
                },
            },
            {
                "title": "Activities - Percentage",
                "payer": members[3],
                "payload": {
                    "title": "Activities - Percentage",
                    "amount": "8888.80",
                    "split_type": "percentage",
                    "splits_input": {
                        members[0]["id"]: "30",
                        members[1]["id"]: "25",
                        members[2]["id"]: "20",
                        members[3]["id"]: "15",
                        members[4]["id"]: "10",
                    },
                },
                "expected_splits": {
                    members[0]["id"]: Decimal("2666.64"),
                    members[1]["id"]: Decimal("2222.20"),
                    members[2]["id"]: Decimal("1777.76"),
                    members[3]["id"]: Decimal("1333.32"),
                    members[4]["id"]: Decimal("888.88"),
                },
            },
            {
                "title": "Airport Cabs - Exact Small Items",
                "payer": members[4],
                "payload": {
                    "title": "Airport Cabs - Exact Small Items",
                    "amount": "1210.45",
                    "split_type": "exact",
                    "splits_input": {
                        members[0]["id"]: "200.10",
                        members[1]["id"]: "210.20",
                        members[2]["id"]: "300.05",
                        members[3]["id"]: "250.05",
                        members[4]["id"]: "250.05",
                    },
                },
                "expected_splits": {
                    members[0]["id"]: Decimal("200.10"),
                    members[1]["id"]: Decimal("210.20"),
                    members[2]["id"]: Decimal("300.05"),
                    members[3]["id"]: Decimal("250.05"),
                    members[4]["id"]: Decimal("250.05"),
                },
            },
        ]

        created_expenses = []
        for expense in expenses_to_create:
            response = await client.post(
                f"/groups/{group_id}/expenses",
                json=expense["payload"],
                headers=auth_headers(expense["payer"]),
            )
            assert response.status_code == 201, response.text
            created = response.json()["data"]
            assert created["title"] == expense["title"]
            assert created["paid_by"] == expense["payer"]["id"]
            assert money(created["amount"]) == money(expense["payload"]["amount"])
            assert created["split_type"] == expense["payload"]["split_type"]
            created_expenses.append({**expense, "id": created["id"]})

        list_expenses_response = await client.get(
            f"/groups/{group_id}/expenses",
            headers=auth_headers(members[2]),
        )
        assert list_expenses_response.status_code == 200, list_expenses_response.text
        listed_expenses = list_expenses_response.json()["data"]
        assert len(listed_expenses) == len(expenses_to_create)
        assert {expense["title"] for expense in listed_expenses} == {
            expense["title"] for expense in expenses_to_create
        }
        assert sum(money(expense["amount"]) for expense in listed_expenses) == Decimal(
            "24635.00"
        )

        splits_by_expense = await fetch_splits_by_expense(
            [expense["id"] for expense in created_expenses]
        )
        for expense in created_expenses:
            actual_splits = splits_by_expense[expense["id"]]
            assert actual_splits == expense["expected_splits"]
            assert sum(actual_splits.values()) == money(expense["payload"]["amount"])
            assert set(actual_splits) <= {member["id"] for member in members}
            assert outsider["id"] not in actual_splits

        (
            expenses_before_failures,
            splits_before_failures,
        ) = await count_group_expenses_and_splits(group_id)

        invalid_requests = [
            (
                auth_headers(outsider),
                {
                    "title": "Outsider Attempt",
                    "amount": "999.00",
                    "split_type": "equal",
                    "equal_member_ids": [member["id"] for member in members],
                },
                403,
            ),
            (
                creator_headers,
                {
                    "title": "Bad Exact Total",
                    "amount": "100.00",
                    "split_type": "exact",
                    "splits_input": {
                        members[0]["id"]: "60.00",
                        members[1]["id"]: "30.00",
                    },
                },
                400,
            ),
            (
                creator_headers,
                {
                    "title": "Bad Percentage Total",
                    "amount": "100.00",
                    "split_type": "percentage",
                    "splits_input": {
                        members[0]["id"]: "70",
                        members[1]["id"]: "20",
                    },
                },
                400,
            ),
            (
                creator_headers,
                {
                    "title": "Outsider In Split",
                    "amount": "100.00",
                    "split_type": "exact",
                    "splits_input": {
                        members[0]["id"]: "50.00",
                        outsider["id"]: "50.00",
                    },
                },
                400,
            ),
        ]

        for headers, payload, expected_status in invalid_requests:
            response = await client.post(
                f"/groups/{group_id}/expenses",
                json=payload,
                headers=headers,
            )
            assert response.status_code == expected_status, response.text

        assert await count_group_expenses_and_splits(group_id) == (
            expenses_before_failures,
            splits_before_failures,
        )
