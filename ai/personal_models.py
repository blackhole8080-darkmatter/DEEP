"""
personal_models.py - Layer 3 of the Deep ML capability stack.

Models built on Aryan's OWN data so Deep becomes "a representation of me".
This first model is a task-completion predictor: given a task's priority, when
it was created, and its due lead-time, predict whether Aryan will actually
complete it - and rank open tasks by how likely they are to get done.

It reads the scheduler's SQLite DB (data/scheduler.db), engineers features, and
reuses the Layer 2 runner (ai/ml_runner) to train/persist a RandomForest. The
saved joblib bundle is then loaded directly for per-task probability scoring.

Cold-start honesty: with too little history (or only one outcome class) we do
NOT train a misleading model - we say so plainly.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import joblib

try:
    from . import ml_runner
except ImportError:  # pragma: no cover - script/relative-import fallback
    import ml_runner  # type: ignore


MIN_SAMPLES = 12          # need enough finished+unfinished history to learn anything
MODEL_NAME = "task_completion"
_PRIORITY = {"low": 0, "med": 1, "high": 2}


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _features_for_row(row: dict[str, Any]) -> dict[str, Any]:
    """Engineer the feature set for one task row (shared by train + predict)."""
    created = _parse_dt(row.get("created"))
    due = _parse_dt(row.get("due"))
    lead_hours = -1.0
    if created and due:
        lead_hours = round((due - created).total_seconds() / 3600.0, 2)
    title = row.get("title") or ""
    return {
        "priority_num": _PRIORITY.get((row.get("priority") or "med").lower(), 1),
        "has_due": 1 if due else 0,
        "lead_time_hours": lead_hours,
        "created_hour": created.hour if created else -1,
        "created_dow": created.weekday() if created else -1,
        "title_len": len(title),
        "title_words": len(title.split()),
    }


def _load_tasks(db_path: str) -> list[dict[str, Any]]:
    if not os.path.exists(db_path):
        return []
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT id, title, due, priority, done, created FROM tasks"
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def _build_df(rows: list[dict[str, Any]], with_label: bool) -> pd.DataFrame:
    records = []
    for r in rows:
        feats = _features_for_row(r)
        if with_label:
            feats["done"] = int(r.get("done") or 0)
        feats["_id"] = r.get("id")
        feats["_title"] = r.get("title")
        records.append(feats)
    return pd.DataFrame(records)


def train_task_completion(db_path: str, models_dir: str) -> str:
    """Train (and persist) the task-completion model from scheduler history."""
    rows = _load_tasks(db_path)
    if len(rows) < MIN_SAMPLES:
        return (
            f"Not enough task history to model you yet: {len(rows)} tasks logged, "
            f"need ~{MIN_SAMPLES}+ (a mix of completed and not). Keep using tasks and "
            f"this will get smarter."
        )
    labels = {int(r.get("done") or 0) for r in rows}
    if len(labels) < 2:
        state = "completed" if 1 in labels else "still open"
        return (
            f"All {len(rows)} logged tasks are {state}, so there's nothing to "
            f"contrast yet. Once you have both done and not-done tasks, I can learn "
            f"what predicts completion."
        )

    df = _build_df(rows, with_label=True).drop(columns=["_id", "_title"])
    report = ml_runner.train(
        df, "random_forest", target="done",
        save_as=MODEL_NAME, models_dir=models_dir,
    )
    return "Task-completion model trained on your history.\n" + report


def predict_task_completion(db_path: str, models_dir: str) -> str:
    """Score OPEN tasks by predicted completion likelihood, ranked."""
    path = os.path.join(models_dir, f"{MODEL_NAME}.joblib")
    if not os.path.exists(path):
        # Train on demand the first time.
        msg = train_task_completion(db_path, models_dir)
        if not os.path.exists(path):
            return msg  # cold-start / single-class message

    rows = _load_tasks(db_path)
    open_rows = [r for r in rows if not int(r.get("done") or 0)]
    if not open_rows:
        return "You have no open tasks to score - all caught up."

    try:
        bundle = joblib.load(path)
        model, features = bundle["model"], bundle["features"]
    except Exception as e:
        return f"Could not load the task model: {e}"

    df = _build_df(open_rows, with_label=False)
    X = df[features].fillna(-1)

    # Probability of completion (class 1) when available; else fall back to label.
    try:
        classes = list(getattr(model, "classes_", [0, 1]))
        idx = classes.index(1) if 1 in classes else len(classes) - 1
        probs = model.predict_proba(X)[:, idx]
    except Exception:
        probs = model.predict(X)

    scored = sorted(
        zip(df["_title"].tolist(), probs), key=lambda t: t[1], reverse=True
    )
    lines = ["Open tasks by predicted likelihood you'll complete them:"]
    for title, p in scored:
        pct = f"{float(p) * 100:.0f}%"
        flag = "likely" if float(p) >= 0.5 else "at risk"
        lines.append(f"  [{pct:>4} {flag}] {title}")
    lines.append("\n(Lower-scored tasks are the ones worth a nudge.)")
    return "\n".join(lines)
