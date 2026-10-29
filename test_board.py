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

    # 项目
    pid = database.create_project("看板测试")
    assert pid is not None
    assert database.create_project("看板测试") is None
    projects = {p["name"]: p["id"] for p in database.list_projects()}
    assert projects["默认"] == 1 and projects["看板测试"] == pid

    # 分区
    s1 = database.add_section(pid, "UI")
    s2 = database.add_section(pid, "数据库")
    assert {s["name"] for s in database.list_sections(pid)} == {"UI", "数据库"}
    assert database.list_sections(1) == []
    database.rename_section(s1, "界面")
    assert {s["name"] for s in database.list_sections(pid)} == {"界面", "数据库"}

    # 卡片 + 进度
    c1 = database.add_card(s1, "看板页面")
    c2 = database.add_card(s1, "详情页", note="含优先级")
    assert database.add_card(s2, "建表")
    i1 = database.add_item(c1, "三列布局", priority=database.PRIORITY_HIGH)
    i2 = database.add_item(c1, "卡片移动", priority=database.PRIORITY_LOW)
    i3 = database.add_item(c1, "进度条")

    cards = database.list_cards(pid)
    by_id = {c["id"]: c for c in cards}
    assert by_id[c1]["section_name"] == "界面"
    assert by_id[c1]["total"] == 3 and by_id[c1]["done"] == 0, by_id[c1]
    assert by_id[c2]["total"] == 0

    database.set_item_status(i1, database.STATUS_DONE)
    assert database.card_progress(c1) == (3, 1)
    assert database.list_cards(pid)[0]["done"] == 1

    # 卡片更新/状态
    database.update_card(c1, title="看板主页面", note="新备注")
    row = database.list_cards(pid)
    by_id = {c["id"]: c for c in row}
    assert by_id[c1]["title"] == "看板主页面"
    database.set_card_status(c1, database.STATUS_DOING)
    by_id = {c["id"]: c for c in database.list_cards(pid)}
    assert by_id[c1]["status"] == database.STATUS_DOING

    # 子项排序（未完成在前）与操作
    ordered = database.list_items(c1)
    assert ordered[0]["status"] == database.STATUS_TODO
    assert ordered[-1]["status"] == database.STATUS_DONE
    database.set_item_status(i2, database.STATUS_DONE)
    ordered = database.list_items(c1)
    assert ordered[0]["status"] == database.STATUS_TODO  # i3 未完成在前
    database.set_item_status(i2, database.STATUS_TODO)
    database.delete_item(i3)
    assert len(database.list_items(c1)) == 2

    # 卡片优先级排序（高在前）
    database.update_card(c1, priority=database.PRIORITY_HIGH)
    row = database.list_cards(pid)
    by_id = {c["id"]: c for c in row}
    assert by_id[c1]["priority"] == database.PRIORITY_HIGH
    assert row[0]["id"] == c1

    # 级联删除
    database.delete_card(c2)
    assert len(database.list_cards(pid)) == 2  # c1 + c3 仍在
    database.delete_section(s2)
    assert len(database.list_cards(pid)) == 1  # c3 随分区删除
    assert {s["name"] for s in database.list_sections(pid)} == {"界面"}  # s1 保留
    database.delete_project(pid)
    assert {p["name"] for p in database.list_projects()} == {"默认"}

    print("ALL BOARD TESTS PASSED")


class LegacyBoardTests(unittest.TestCase):
    def test_legacy_checks(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    run_checks()
