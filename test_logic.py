"""Legacy smoke checks run in a subprocess to isolate database and Qt state."""
import subprocess
import sys
import unittest
from pathlib import Path


def run_checks():
    import os
    import sys
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    test_dir = tempfile.mkdtemp()
    os.chdir(test_dir)

    import database

    database.DB_PATH = os.path.join(test_dir, "test.db")
    database.init_db()
    assert database.get_settings()["work_minutes"] == "25"
    assert database.get_settings()["sound_effect"] == "chime"
    assert database.list_projects()[0]["name"] == "默认"

    rid = database.start_record(25)
    database.complete_record(rid)
    rid2 = database.start_record(25)
    rid3 = database.start_record(25)
    database.finish_record(rid3)

    counts = database.counts_since(7)
    assert counts[-1][1] == 1, counts
    summary = database.summary(7)
    assert summary["count"] == 1 and summary["minutes"] == 25, summary
    assert summary["started"] == 3, summary
    assert len(database.recent(10)) == 3

    rid4 = database.start_record(0, "stopwatch", 1)
    database.complete_record(rid4)
    today_prefix = database.datetime_now()[:10]
    with database._conn() as conn:
        conn.execute(
            "UPDATE records SET start_time = ?, end_time = ? WHERE id = ?",
            (f"{today_prefix}T00:00:00", f"{today_prefix}T00:02:00", rid4),
        )
    summary = database.summary(7)
    assert summary["count"] == 2 and summary["minutes"] == 27, summary
    assert database.recent(10)[0]["minutes"] == 2, database.recent(10)[0]["minutes"]

    pid = database.create_project("学习")
    assert pid is not None
    assert database.create_project("学习") is None
    rid5 = database.start_record(25, "countdown", pid)
    database.complete_record(rid5)
    assert database.summary_total(pid)["count"] == 1
    assert database.summary_total()["count"] == 3
    assert database.delete_project(pid) is True
    assert database.summary_total()["count"] == 3
    assert database.delete_project(1) is False
    assert database.list_projects()[0]["name"] == "默认"

    with database._conn() as conn:
        conn.execute("DROP TABLE records")
        conn.execute(
            "CREATE TABLE records ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "start_time TEXT NOT NULL,"
            "end_time TEXT,"
            "planned_minutes INTEGER,"
            "completed INTEGER DEFAULT 0)"
        )
    database.init_db()
    columns = [r["name"] for r in database._conn().execute("PRAGMA table_info(records)")]
    assert "mode" in columns and "project_id" in columns, columns

    database.save_settings({"work_minutes": 45})
    assert database.get_settings()["work_minutes"] == "45"

    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication([])
    from timer_logic import PomodoroTimer

    state = {"settings": database.get_settings()}
    timer = PomodoroTimer(lambda: state["settings"])
    assert timer.phase == "work" and timer.remaining == 45 * 60

    completed = []
    timer.work_completed.connect(completed.append)
    timer._advance(completed_work=True)
    assert timer.phase == "short" and timer.completed_in_cycle == 1, timer.phase
    timer._advance(completed_work=False)
    assert timer.phase == "work"
    timer._advance(completed_work=True)
    timer._advance(completed_work=True)
    timer._advance(completed_work=True)
    timer._advance(completed_work=True)
    timer._advance(completed_work=True)
    assert timer.phase == "long", timer.phase
    assert completed == [1, 2, 3, 4], completed

    assert timer.set_mode("stopwatch") is True
    assert timer.elapsed == 0
    timer.start()
    timer._on_tick()
    timer._on_tick()
    timer._on_tick()
    assert timer.elapsed == 3, timer.elapsed
    finished = []
    timer.stopwatch_finished.connect(finished.append)
    timer.stop_stopwatch()
    assert finished == [3], finished
    assert timer.elapsed == 0
    assert timer.set_mode("countdown") is True
    assert timer.remaining == timer.total

    print("ALL LOGIC TESTS PASSED")


class LegacyTimerTests(unittest.TestCase):
    def test_legacy_checks(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    run_checks()
