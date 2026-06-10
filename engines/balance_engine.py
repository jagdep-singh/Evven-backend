from decimal import Decimal
from uuid import UUID


def compute_raw_balance(
    expenses_paid: list, user_splits: list, user_id: UUID
) -> dict[UUID, Decimal]:
    balances: dict[UUID, Decimal] = {}

    for expense in expenses_paid:
        for split in expense.splits:
            if split.user_id == user_id:
                continue
            balances[split.user_id] = balances.get(
                split.user_id, Decimal("0")
            ) + Decimal(str(split.amount))

    for split in user_splits:
        payer_id = split.expense.paid_by
        if payer_id == user_id:
            continue
        balances[payer_id] = balances.get(payer_id, Decimal("0")) - Decimal(
            str(split.amount)
        )

    return balances


def apply_settlements(
    balances: dict[UUID, Decimal], payments_made: list, payments_received: list
) -> dict[UUID, Decimal]:
    for settlement in payments_made:
        receiver_id = settlement.receiver_id
        balances[receiver_id] = balances.get(receiver_id, Decimal("0")) + Decimal(
            str(settlement.amount)
        )

    for settlement in payments_received:
        payer_id = settlement.payer_id
        balances[payer_id] = balances.get(payer_id, Decimal("0")) - Decimal(
            str(settlement.amount)
        )

    return {uid: amt for uid, amt in balances.items() if amt != Decimal("0")}


def compute_category_totals(expenses: list) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    grand_total = Decimal("0")

    for expense in expenses:
        category = expense.category or "Uncategorized"
        amount = Decimal(str(expense.amount))
        totals[category] = totals.get(category, Decimal("0")) + amount
        grand_total += amount

    totals["__total__"] = grand_total
    return totals
