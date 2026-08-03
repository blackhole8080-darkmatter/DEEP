# deep/scheduler.py — Task Scheduling (Bible Section 26.6)
"""APScheduler BackgroundScheduler wrapper. Falls back to threading.Timer if
APScheduler isn't installed."""
from __future__ import annotations

import threading
import time

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHED = True
except Exception:  # pragma: no cover
    APSCHED = False


class TaskScheduler:
    def __init__(self, config=None):
        self.config = config
        self._sched = None
        self._fallback_jobs = {}
        if APSCHED:
            self._sched = BackgroundScheduler()
            self._sched.start()

    def schedule_task(self, fn, args=None, trigger=None, task_id=None) -> dict:
        trigger = trigger or {"type": "interval", "seconds": 60}
        task_id = task_id or f"task_{int(time.time())}"
        args = args or {}
        if self._sched is not None:
            ttype = trigger.get("type", "interval")
            if ttype == "interval":
                job = self._sched.add_job(fn, "interval",
                                          seconds=trigger.get("seconds", 60),
                                          id=task_id, kwargs=args)
            elif ttype == "cron":
                job = self._sched.add_job(fn, "cron", hour=trigger.get("hour", 0),
                                          minute=trigger.get("minute", 0),
                                          id=task_id, kwargs=args)
            else:  # once
                job = self._sched.add_job(fn, "date", run_date=trigger.get("run_date"),
                                          id=task_id, kwargs=args)
            return {"job_id": task_id, "next_run": str(job.next_run_time), "result": task_id,
                    "verbal": f"Scheduled task {task_id}, sir."}
        # threading fallback (interval only)
        secs = trigger.get("seconds", 60)

        def loop():
            while task_id in self._fallback_jobs:
                time.sleep(secs)
                try:
                    fn(**args)
                except Exception:
                    pass
        t = threading.Thread(target=loop, daemon=True)
        self._fallback_jobs[task_id] = t
        t.start()
        return {"job_id": task_id, "result": task_id,
                "verbal": f"Scheduled task {task_id} (threading fallback), sir."}

    def list_tasks(self) -> dict:
        if self._sched is not None:
            jobs = [{"id": j.id, "next_run": str(j.next_run_time)}
                    for j in self._sched.get_jobs()]
        else:
            jobs = [{"id": k} for k in self._fallback_jobs]
        return {"tasks": jobs, "result": len(jobs),
                "verbal": f"{len(jobs)} scheduled task(s), sir."}

    def cancel_task(self, task_id) -> dict:
        if self._sched is not None:
            try:
                self._sched.remove_job(task_id)
                return {"success": True, "verbal": f"Cancelled {task_id}, sir."}
            except Exception:
                return {"success": False, "verbal": f"No such task {task_id}, sir."}
        self._fallback_jobs.pop(task_id, None)
        return {"success": True, "verbal": f"Cancelled {task_id}, sir."}

    def test(self) -> None:
        out = self.schedule_task(lambda: None, trigger={"type": "interval", "seconds": 3600},
                                 task_id="selftest")
        assert out["job_id"] == "selftest"
        assert self.list_tasks()["result"] >= 1
        self.cancel_task("selftest")
        print("scheduler.TaskScheduler: OK")


def test() -> None:
    TaskScheduler().test()


if __name__ == "__main__":
    test()
