"""
core/integrations/personal_finance.py — Personal Finance Engine for DEEP

Local-first transaction tracking, budgeting, and spending intelligence.
Bank connections (Plaid / Nordigen) are optional — everything works with
manual CSV import + smart categorisation.

SQLite schema (data/finance.db):
  transactions  — every txn: date, amount, currency, description, category, source
  budgets     — per-category monthly budgets
  bills       — recurring subscriptions / bills with due dates
  accounts    — manual account balances (cash, savings, investment…)
  categories  — keyword → category rules + LLM fallback

Tools exposed:
  - add_transaction, list_transactions, spending_summary
  - set_budget, get_budget_status
  - add_bill, list_bills, upcoming_bills
  - detect_spending_anomalies
  - import_csv

Graceful degradation: without bank API keys, DEEP still tracks everything
you tell it or import manually.
"""

from __future__ import annotations

import csv
import io
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "finance.db"

# ── default category rules (keyword → category) ────────────────────────────
_DEFAULT_RULES: Dict[str, str] = {
    "salary": "income", "wage": "income", "deposit": "income",
    "rent": "housing", "mortgage": "housing", "housing": "housing",
    "grocery": "food", "supermarket": "food", "restaurant": "food",
    "uber": "transport", "taxi": "transport", "fuel": "transport", "train": "transport",
    "electric": "utilities", "water": "utilities", "internet": "utilities", "phone": "utilities",
    "netflix": "subscriptions", "spotify": "subscriptions", "subscription": "subscriptions",
    "gym": "health", "pharmacy": "health", "doctor": "health",
    "amazon": "shopping", "zalando": "shopping", "clothing": "shopping",
    "steam": "entertainment", "game": "entertainment", "cinema": "entertainment",
    "transfer": "transfer", "withdrawal": "transfer",
}


class PersonalFinanceEngine:
    """DEEP's personal finance brain. Works offline; bank APIs optional."""

    def __init__(self, db_path: Optional[str] = None):
        self.db = db_path or str(_DB_PATH)
        self._init_schema()
        self._seed_defaults()

    # ── schema ───────────────────────────────────────────────────────────────
    def _init_schema(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'SEK',
                    description TEXT,
                    category TEXT DEFAULT 'uncategorised',
                    source TEXT DEFAULT 'manual',
                    account TEXT DEFAULT 'default',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
                CREATE INDEX IF NOT EXISTS idx_txn_cat ON transactions(category);

                CREATE TABLE IF NOT EXISTS budgets (
                    category TEXT PRIMARY KEY,
                    monthly_limit REAL NOT NULL,
                    currency TEXT DEFAULT 'SEK',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS bills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'SEK',
                    frequency TEXT DEFAULT 'monthly',  -- monthly, weekly, yearly
                    next_due TEXT,
                    active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS accounts (
                    name TEXT PRIMARY KEY,
                    balance REAL NOT NULL DEFAULT 0,
                    currency TEXT DEFAULT 'SEK',
                    type TEXT DEFAULT 'checking'  -- checking, savings, investment, crypto
                );

                CREATE TABLE IF NOT EXISTS category_rules (
                    keyword TEXT PRIMARY KEY,
                    category TEXT NOT NULL
                );
            """)

    def _seed_defaults(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            existing = {r[0] for r in conn.execute("SELECT keyword FROM category_rules")}
            new = [(k, v) for k, v in _DEFAULT_RULES.items() if k not in existing]
            if new:
                conn.executemany("INSERT INTO category_rules (keyword, category) VALUES (?, ?)", new)

    # ── categorisation ───────────────────────────────────────────────────────
    def _categorise(self, description: str) -> str:
        low = description.lower()
        with closing(sqlite3.connect(self.db)) as conn, conn:
            for keyword, category in conn.execute("SELECT keyword, category FROM category_rules"):
                if keyword in low:
                    return category
        return "uncategorised"

    def add_rule(self, keyword: str, category: str) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO category_rules (keyword, category) VALUES (?, ?)",
                (keyword.lower(), category.lower()),
            )

    # ── transactions ───────────────────────────────────────────────────────────
    def add_transaction(
        self,
        date: str,
        amount: float,
        description: str,
        currency: str = "SEK",
        category: Optional[str] = None,
        source: str = "manual",
        account: str = "default",
    ) -> Dict[str, Any]:
        cat = category or self._categorise(description)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            cur = conn.execute(
                "INSERT INTO transactions (date, amount, currency, description, category, source, account) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date, amount, currency, description, cat, source, account),
            )
            txn_id = cur.lastrowid
            # update account balance
            conn.execute(
                "INSERT INTO accounts (name, balance, currency) VALUES (?, 0, ?) ON CONFLICT(name) DO NOTHING",
                (account, currency),
            )
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE name = ?",
                (amount, account),
            )
        return {"id": txn_id, "category": cat, "verbal": f"Recorded {amount:,.2f} {currency} under {cat}."}

    def list_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        where = ["1=1"]
        params: List[Any] = []
        if start_date:
            where.append("date >= ?"); params.append(start_date)
        if end_date:
            where.append("date <= ?"); params.append(end_date)
        if category:
            where.append("category = ?"); params.append(category)
        sql = f"SELECT * FROM transactions WHERE {' AND '.join(where)} ORDER BY date DESC LIMIT ?"
        params.append(limit)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def spending_summary(self, months: int = 1) -> Dict[str, Any]:
        """Aggregate spending by category for the last N months."""
        start = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT category, SUM(amount) as total, COUNT(*) as count FROM transactions WHERE date >= ? GROUP BY category ORDER BY total ASC",
                (start,),
            ).fetchall()
        cats = [dict(r) for r in rows]
        total = sum(r["total"] for r in cats if r["total"] < 0)
        income = sum(r["total"] for r in cats if r["total"] > 0)
        return {
            "period_months": months,
            "start_date": start,
            "total_spent": round(total, 2),
            "total_income": round(income, 2),
            "net": round(income + total, 2),
            "by_category": cats,
            "verbal": f"Last {months} month(s): spent {abs(total):,.2f}, income {income:,.2f}, net {income + total:,.2f}.",
        }

    # ── budgets ──────────────────────────────────────────────────────────────
    def set_budget(self, category: str, limit: float, currency: str = "SEK") -> Dict[str, Any]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO budgets (category, monthly_limit, currency) VALUES (?, ?, ?)",
                (category.lower(), limit, currency),
            )
        return {"verbal": f"Budget for {category} set to {limit:,.2f} {currency}/month."}

    def get_budget_status(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            budgets = conn.execute("SELECT * FROM budgets").fetchall()
            result = []
            for b in budgets:
                spent = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE category = ? AND date >= ? AND amount < 0",
                    (b["category"], month_start),
                ).fetchone()[0]
                limit = b["monthly_limit"]
                result.append({
                    "category": b["category"],
                    "limit": limit,
                    "spent": round(abs(spent), 2),
                    "remaining": round(limit - abs(spent), 2),
                    "percent": round((abs(spent) / limit) * 100, 1) if limit else 0,
                    "currency": b["currency"],
                })
        return result

    # ── bills / subscriptions ──────────────────────────────────────────────────
    def add_bill(self, name: str, amount: float, frequency: str = "monthly", next_due: Optional[str] = None, currency: str = "SEK") -> Dict[str, Any]:
        due = next_due or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            cur = conn.execute(
                "INSERT INTO bills (name, amount, currency, frequency, next_due) VALUES (?, ?, ?, ?, ?)",
                (name, amount, currency, frequency, due),
            )
        return {"id": cur.lastrowid, "verbal": f"Bill '{name}' ({amount:,.2f} {currency}, {frequency}) added, next due {due}."}

    def list_bills(self, active_only: bool = True) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM bills WHERE active = 1 ORDER BY next_due" if active_only else "SELECT * FROM bills ORDER BY next_due"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def upcoming_bills(self, days: int = 14) -> List[Dict[str, Any]]:
        cutoff = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM bills WHERE active = 1 AND next_due <= ? ORDER BY next_due",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── anomaly detection ────────────────────────────────────────────────────
    def detect_anomalies(self, category: Optional[str] = None, lookback_months: int = 3) -> List[Dict[str, Any]]:
        """Flag transactions that are >2 std-dev from the mean in their category."""
        import statistics

        start = (datetime.now() - timedelta(days=30 * lookback_months)).strftime("%Y-%m-%d")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            if category:
                cats = [category]
            else:
                cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM transactions WHERE date >= ? AND amount < 0", (start,))]

            anomalies = []
            for cat in cats:
                amounts = [r[0] for r in conn.execute(
                    "SELECT amount FROM transactions WHERE category = ? AND date >= ? AND amount < 0",
                    (cat, start),
                )]
                if len(amounts) < 3:
                    continue
                mean = statistics.mean(amounts)
                std = statistics.stdev(amounts) if len(amounts) > 1 else 0
                if std == 0:
                    continue
                # recent transactions in this category
                recent = conn.execute(
                    "SELECT * FROM transactions WHERE category = ? AND date >= ? AND amount < 0 ORDER BY date DESC LIMIT 5",
                    (cat, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")),
                ).fetchall()
                for row in recent:
                    z = (row["amount"] - mean) / std
                    if abs(z) > 2:
                        anomalies.append({
                            "transaction_id": row["id"],
                            "date": row["date"],
                            "description": row["description"],
                            "amount": row["amount"],
                            "category": cat,
                            "z_score": round(z, 2),
                            "verbal": f"Unusual {cat} spend: {row['description']} ({row['amount']:,.2f}) — {z:.1f}σ from average.",
                        })
            return anomalies

    # ── CSV import ─────────────────────────────────────────────────────────────
    def import_csv(self, text: str, date_col: str = "date", amount_col: str = "amount", desc_col: str = "description", delimiter: str = ",") -> Dict[str, Any]:
        """Import a CSV string. Flexible column mapping."""
        try:
            rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
        except Exception as e:
            return {"ok": False, "verbal": f"CSV parse error: {e}"}

        imported = 0
        for row in rows:
            try:
                date = row.get(date_col, datetime.now().strftime("%Y-%m-%d"))
                amount = float(str(row.get(amount_col, "0")).replace(",", "").replace(" ", ""))
                desc = row.get(desc_col, "")
                if amount == 0 or not desc:
                    continue
                self.add_transaction(date, amount, desc, source="csv")
                imported += 1
            except Exception:
                continue
        return {"ok": True, "imported": imported, "verbal": f"Imported {imported} transactions from CSV."}

    # ── accounts ─────────────────────────────────────────────────────────────
    def get_accounts(self) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    # ── high-level verbal summary for the brain ──────────────────────────────
    def verbal_summary(self) -> str:
        s = self.spending_summary(months=1)
        upcoming = self.upcoming_bills(days=14)
        budgets = self.get_budget_status()
        parts = [
            f"This month: spent {abs(s['total_spent']):,.2f}, income {s['total_income']:,.2f}, net {s['net']:,.2f}.",
        ]
        if upcoming:
            parts.append(f"Upcoming bills ({len(upcoming)}): " + ", ".join(f"{b['name']} ({b['amount']:,.0f})" for b in upcoming[:3]))
        overspent = [b for b in budgets if b["percent"] > 100]
        if overspent:
            parts.append("Over-budget categories: " + ", ".join(f"{b['category']} ({b['percent']:.0f}%)" for b in overspent))
        return " ".join(parts)


# ── singleton export ─────────────────────────────────────────────────────────
_finance = PersonalFinanceEngine()


def add_transaction(date: str, amount: float, description: str, **kwargs):
    return _finance.add_transaction(date, amount, description, **kwargs)


def list_transactions(**kwargs):
    return _finance.list_transactions(**kwargs)


def spending_summary(**kwargs):
    return _finance.spending_summary(**kwargs)


def set_budget(category: str, limit: float, currency: str = "SEK"):
    return _finance.set_budget(category, limit, currency)


def get_budget_status():
    return _finance.get_budget_status()


def add_bill(name: str, amount: float, **kwargs):
    return _finance.add_bill(name, amount, **kwargs)


def upcoming_bills(days: int = 14):
    return _finance.upcoming_bills(days)


def detect_anomalies(**kwargs):
    return _finance.detect_anomalies(**kwargs)


def import_csv(text: str, **kwargs):
    return _finance.import_csv(text, **kwargs)


def get_accounts():
    return _finance.get_accounts()


def verbal_summary():
    return _finance.verbal_summary()


# CLI smoke-test
if __name__ == "__main__":
    f = PersonalFinanceEngine()
    print(f.add_transaction("2026-06-01", -450.0, "ICA Supermarket"))
    print(f.add_transaction("2026-06-02", -1200.0, "Rent June"))
    print(f.add_transaction("2026-06-03", 15000.0, "Salary"))
    print(f.set_budget("food", 3000))
    print(f.set_budget("housing", 12000))
    print(f.get_budget_status())
    print(f.spending_summary())
    print(f.verbal_summary())
