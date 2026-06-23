"""Finance domain endpoints."""
from datetime import datetime
from fastapi import APIRouter
from core.integrations.personal_finance import PersonalFinanceEngine

router = APIRouter(prefix="/api/finance", tags=["finance"])
_finance_api = PersonalFinanceEngine()

@router.get("/summary")
async def finance_summary(months: int = 1):
    return _finance_api.spending_summary(months=months)

@router.get("/transactions")
async def finance_transactions(start: str = None, end: str = None, category: str = None, limit: int = 100):
    return {"transactions": _finance_api.list_transactions(start_date=start, end_date=end, category=category, limit=limit)}

@router.post("/transaction")
async def finance_add_transaction(data: dict):
    return _finance_api.add_transaction(
        data.get("date", datetime.now().strftime("%Y-%m-%d")),
        float(data.get("amount", 0)),
        data.get("description", ""),
        category=data.get("category"),
        currency=data.get("currency", "SEK"),
        account=data.get("account", "default"),
    )

@router.get("/budgets")
async def finance_budgets():
    return {"budgets": _finance_api.get_budget_status()}

@router.post("/budget")
async def finance_set_budget(data: dict):
    return _finance_api.set_budget(data.get("category", ""), float(data.get("limit", 0)), data.get("currency", "SEK"))

@router.get("/bills")
async def finance_bills():
    return {"bills": _finance_api.list_bills()}

@router.get("/bills/upcoming")
async def finance_upcoming_bills(days: int = 14):
    return {"bills": _finance_api.upcoming_bills(days=days)}

@router.post("/bill")
async def finance_add_bill(data: dict):
    return _finance_api.add_bill(
        data.get("name", ""), float(data.get("amount", 0)),
        frequency=data.get("frequency", "monthly"),
        next_due=data.get("next_due"),
        currency=data.get("currency", "SEK"),
    )

@router.get("/anomalies")
async def finance_anomalies(category: str = None):
    return {"anomalies": _finance_api.detect_anomalies(category=category)}

@router.get("/accounts")
async def finance_accounts():
    return {"accounts": _finance_api.get_accounts()}

@router.post("/import")
async def finance_import_csv(data: dict):
    return _finance_api.import_csv(
        data.get("csv", ""),
        date_col=data.get("date_col", "date"),
        amount_col=data.get("amount_col", "amount"),
        desc_col=data.get("desc_col", "description"),
        delimiter=data.get("delimiter", ","),
    )
