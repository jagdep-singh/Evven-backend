from collections import defaultdict
from decimal import Decimal
from uuid import UUID

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
        payed_by = expense['payer_id']
        
        for split in expense['splits']:
            split_user_id = split['user_id']
            amount = Decimal(split['amount'])
            
            if split_user_id == payed_by:
                continue
            
            breakdown[split_user_id][payed_by].append(
                    {
                        "expense_id": expense["expense_id"],
                        "title": expense["title"],
                        "amount": amount,
                    }
                )
    return {
            debtor: dict(creditors)
            for debtor, creditors in breakdown.items()
        }