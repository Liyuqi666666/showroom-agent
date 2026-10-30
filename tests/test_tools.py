"""测试实际工具行为；这些是工具层测试，不是大模型/Agent 效果评测。"""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import robot_tools as tools


class RobotToolsTests(unittest.TestCase):
    def setUp(self):
        tools.reset_robot()

    def test_initial_state(self):
        state = tools.get_robot_status()["data"]
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["current_area"], "入口")

    def test_returned_state_is_a_copy(self):
        tools.get_robot_status()["data"]["status"] = "offline"
        self.assertEqual(tools.get_robot_status()["data"]["status"], "idle")

    def test_normal_navigation_updates_location(self):
        self.assertTrue(tools.navigate_to("机器人展区")["success"])
        self.assertEqual(tools.get_robot_status()["data"]["current_area"], "机器人展区")

    def test_all_valid_areas(self):
        for area in tools.AREAS:
            with self.subTest(area=area):
                self.assertEqual(tools.navigate_to(area)["data"]["current_area"], area)

    def test_navigation_trims_whitespace(self):
        self.assertTrue(tools.navigate_to("  工业展区  ")["success"])

    def test_unknown_area_does_not_move(self):
        self.assertEqual(tools.navigate_to("月球")["code"], "UNKNOWN_AREA")
        self.assertEqual(tools.get_robot_status()["data"]["current_area"], "入口")

    def test_empty_area(self):
        self.assertEqual(tools.navigate_to("  ")["code"], "INVALID_ARGUMENT")

    def test_non_string_area(self):
        self.assertEqual(tools.navigate_to(None)["code"], "INVALID_ARGUMENT")

    def test_busy_blocks_navigation(self):
        tools.reset_robot("busy")
        self.assertEqual(tools.navigate_to("工业展区")["code"], "ROBOT_BUSY")
        self.assertEqual(tools.get_robot_status()["data"]["current_area"], "入口")

    def test_offline_blocks_navigation(self):
        tools.reset_robot("offline")
        self.assertEqual(tools.navigate_to("工业展区")["code"], "ROBOT_OFFLINE")

    def test_navigation_failure_does_not_move(self):
        tools.reset_robot("navigation_failure")
        self.assertEqual(tools.navigate_to("工业展区")["code"], "NAVIGATION_FAILED")
        self.assertEqual(tools.get_robot_status()["data"]["current_area"], "入口")

    def test_timeout_marks_position_unconfirmed(self):
        tools.reset_robot("timeout")
        result = tools.navigate_to("工业展区")
        self.assertEqual(result["code"], "TIMEOUT")
        self.assertEqual(result["data"]["status"], "unknown")
        self.assertFalse(result["data"]["position_confirmed"])

    def test_timeout_blocks_repeat_action(self):
        tools.reset_robot("timeout")
        tools.navigate_to("工业展区")
        self.assertEqual(tools.navigate_to("工业展区")["code"], "STATE_UNKNOWN")

    def test_already_at_target(self):
        tools.navigate_to("工业展区")
        self.assertEqual(tools.navigate_to("工业展区")["code"], "ALREADY_THERE")

    def test_reset_restores_environment(self):
        tools.reset_robot("timeout")
        tools.navigate_to("工业展区")
        tools.reset_robot()
        self.assertTrue(tools.navigate_to("机器人展区")["success"])

    def test_invalid_scenario_preserves_state(self):
        before = tools.get_robot_status()
        with self.assertRaises(ValueError):
            tools.reset_robot("invalid")
        self.assertEqual(tools.get_robot_status(), before)

    def test_search_by_name(self):
        result = tools.search_product_info("导览机器人A")
        self.assertEqual(result["data"]["total"], 1)
        self.assertEqual(result["data"]["products"][0]["id"], "guide_robot_a")

    def test_search_by_area(self):
        product = tools.search_product_info("工业展区")["data"]["products"][0]
        self.assertEqual(product["name"], "工业机械臂B")

    def test_search_by_capability(self):
        self.assertEqual(tools.search_product_info("语音讲解")["data"]["total"], 1)

    def test_search_normalizes_spaces_and_case(self):
        self.assertEqual(tools.search_product_info("导览机器人 a")["data"]["total"], 1)

    def test_no_matching_product(self):
        result = tools.search_product_info("水下探测器")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["products"], [])

    def test_invalid_queries(self):
        for query in (None, 123, "", "  ", "？"):
            with self.subTest(query=query):
                self.assertEqual(tools.search_product_info(query)["code"], "INVALID_ARGUMENT")

    def test_sources_resolve_to_actual_records(self):
        result = tools.search_product_info("机器人")
        for product in result["data"]["products"]:
            relative, record_id = product["source"].split("#")
            path = Path(tools.__file__).parent / relative
            records = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(record_id, [record["id"] for record in records])
            self.assertTrue(product["fictional"])

    def test_missing_knowledge_file(self):
        with patch.object(Path, "read_text", side_effect=FileNotFoundError("missing.json")):
            self.assertEqual(tools.search_product_info("机器人")["code"], "KNOWLEDGE_ERROR")

    def test_invalid_knowledge_content(self):
        for content in ("{", "{}", '[{"id":"bad"}]'):
            with self.subTest(content=content):
                with patch.object(Path, "read_text", return_value=content):
                    self.assertEqual(tools.search_product_info("机器人")["code"], "KNOWLEDGE_ERROR")


if __name__ == "__main__":
    unittest.main()
