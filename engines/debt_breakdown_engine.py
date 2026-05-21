from collections import defaultdict, deque
from decimal import Decimal


def build_debt_breakdown(
    expenses: list[dict],
) -> dict:
    """
    Expected expense structure:

    [
        {
            "expense_id": UUID,
            "title": str,
            "paid_by": UUID,
            "splits": [
                {
                    "user_id": UUID,
                    "amount": Decimal,
                }
            ]
        }
    ]

    Each expense contains:
    - the user who originally paid (`paid_by`)
    - split entries showing how much each participant owes

    For every split:
    - if the split user is NOT the payer,
      then that user owes the payer their split amount.

    Returns a nested structure in the format:

    {
        debtor_id: {
            creditor_id: [
                {
                    "expense_id": UUID,
                    "title": str,
                    "amount": Decimal,
                }
            ]
        }
    }
    """
    breakdown = defaultdict(lambda: defaultdict(list))

    for expense in expenses:
        paid_by = expense["paid_by"]

        for split in expense["splits"]:
            split_user_id = split["user_id"]
            amount = Decimal(split["amount"])

            if split_user_id == paid_by:
                continue

            breakdown[split_user_id][paid_by].append(
                {
                    "expense_id": expense["expense_id"],
                    "title": expense["title"],
                    "amount": amount,
                }
            )
    return {debtor: dict(creditors) for debtor, creditors in breakdown.items()}


def aggregate_debt(breakdown: dict) -> dict:
    """
    aggregates all expense-level debts into total debt amounts between users.
    accepts:
    {
        "debtor": {
            "creditor": [
                {"amount": Decimal("400")},
                {"amount": Decimal("250")},
            ]
        }
    }

    returns:
    {
        "debtor": {
            "creditor": Decimal("650"),
        }
    }
    """

    aggregated_debt = defaultdict(dict)
    for debtor, creditors in breakdown.items():
        for creditor, entries in creditors.items():
            total_amount = sum(entry["amount"] for entry in entries)
            aggregated_debt[debtor][creditor] = total_amount

    return {debtor: dict(creditors) for debtor, creditors in aggregated_debt.items()}


def simplify_debt(aggregated_debt: dict) -> dict:
    """
    simplifies reverse debts between users by keeping only the net debt direction.

    accepts:
    {
        "debtor": {
            "creditor": Decimal("500"),
        },
        "creditor": {
            "debtor": Decimal("200"),
        }
    }

    returns:
    {
        "debtor": {
            "creditor": Decimal("300"),
        }
    }
    """

    simplified_debt = defaultdict(dict)

    for debtor, creditors in aggregated_debt.items():
        for creditor, amount in creditors.items():
            reverse_amount = aggregated_debt.get(creditor, {}).get(debtor, Decimal(0))

            if amount > reverse_amount:
                simplified_debt[debtor][creditor] = abs(amount - reverse_amount)

    return {debtor: dict(creditors) for debtor, creditors in simplified_debt.items()}


def settle_debt(aggregated_debt: dict) -> dict:
    net_balance = defaultdict(Decimal)
    for debtor, creditors in aggregated_debt.items():
        for creditor, amount in creditors.items():
            amount = Decimal(str(amount))
            net_balance[debtor] -= amount
            net_balance[creditor] += amount

    debtors = deque()
    creditors = deque()

    for user_id, balance in net_balance.items():
        rounded_balance = balance.quantize(Decimal("0.01"))
        if rounded_balance < Decimal("0.00"):
            debtors.append(
                {
                    "user_id": user_id,
                    "amount": abs(rounded_balance),
                }
            )
        elif rounded_balance > Decimal("0.00"):
            creditors.append(
                {
                    "user_id": user_id,
                    "amount": rounded_balance,
                }
            )
    settled = defaultdict(dict)

    while debtors and creditors:
        debtor = debtors[0]
        creditor = creditors[0]

        settlement_amount = min(debtor["amount"], creditor["amount"])
        settled[debtor["user_id"]][creditor["user_id"]] = settlement_amount

        debtor["amount"] -= settlement_amount
        creditor["amount"] -= settlement_amount

        debtor["amount"] = debtor["amount"].quantize(Decimal("0.01"))
        creditor["amount"] = creditor["amount"].quantize(Decimal("0.01"))

        if debtor["amount"] == 0:
            debtors.popleft()

        if creditor["amount"] == 0:
            creditors.popleft()

    return {debtor: dict(creditors) for debtor, creditors in settled.items()}


def calculate_net_balance(aggregated_debt: dict, user_id: str) -> Decimal:
    """
    Calculates the net balance for a user from aggregated debt data.
        expects:
        {
            debtor_id: {
                creditor_id: Decimal
                }
        }
    """
    balance = Decimal(0)
    for debtor, creditors in aggregated_debt.items():
        for creditor, amount in creditors.items():
            if debtor == user_id:
                balance -= amount
            elif creditor == user_id:
                balance += amount
    return balance
