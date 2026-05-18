# from decimal import Decimal
# from uuid import UUID

# from sqlalchemy.orm import Session

# from models.personal_expenses import PersonalExpense
# from models.group_expenses import GroupExpense
# from models.expense_split import ExpenseSplit
# from models.settlements import Settlement

# def calculate_balances(
#         user_id : UUID,
#         group_id : UUID,
#         db : Session
#     ) -> dict[UUID,Decimal]:

#     balances: dict[UUID,Decimal] = {}

#     expenses_paid = {
#         db.query(GroupExpense)
#         .filter(GroupExpense.group_id == group_id, GroupExpense.paid_by == user_id)
#         .all()
#     }

#     for expense in expenses_paid:
#         for split in expense.splits:
#             if split.user_id == user_id:
#                 continue
#             balances[split.user_id] = (
#                 balances.get(split.user_id, Decimal("0")) + Decimal(str(split.amount))
#             )

#     # user_splits = (
#     #     db.query(ExpenseSplit)
#     #     .join(GroupExpense, ExpenseSplit.expense_id == )
#     # )


# def track_debts(

#     ) -> dict[UUID,Decimal]:


# def aggregate_totals(
#         user_id: UUID,
#         db: Session
#     ) -> dict[str, Decimal]:
#     expenses = {
#         db.query(PersonalExpense)
#         .filter(PersonalExpense.user_id == user_id)
#         .all()
#     }

#     totals : dict[str,Decimal] = {}
#     grand_total = Decimal("0")

#     for expense in expenses:
#         category = expense.category or "Uncategorised"
#         amount = Decimal(str(expense.amount))
#         totals[category] = totals.get(category, Decimal("0")) + amount
#         grand_total += amount

#     totals["__totals__"] = grand_total
#     return totals
