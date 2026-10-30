"""不联网：用模型替身验证工具执行、上限和失败后的状态。"""

import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

from agent import AgentLimitError, ShowroomAgent, execute_tool
from model_config import ModelConfig, friendly_error, load_config
from robot_tools import get_robot_status, reset_robot


def call(name, args=None, index=1):
    return AIMessage(content="", tool_calls=[{
        "name": name, "args": args or {}, "id": f"call_{index}", "type": "tool_call",
    }])


class FakeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        self.requests.append(list(messages))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class AgentTests(unittest.TestCase):
    def setUp(self):
        reset_robot()

    def test_tools_execute_and_results_return_to_model(self):
        fake = FakeModel([
            call("get_robot_status"), call("navigate_to", {"area": "机器人展区"}, 2),
            call("search_product_info", {"query": "机器人展区"}, 3), AIMessage(content="演示完成"),
        ])
        agent = ShowroomAgent(fake)
        self.assertEqual(agent.ask("带路并介绍"), "演示完成")
        self.assertEqual(get_robot_status()["data"]["current_area"], "机器人展区")
        results = [m for m in fake.requests[-1] if isinstance(m, ToolMessage)]
        self.assertEqual(len(results), 3)
        self.assertIn("knowledge/products.json#guide_robot_a", results[-1].content)

    def test_busy_cannot_be_bypassed_by_model(self):
        reset_robot("busy")
        result = execute_tool("navigate_to", {"area": "机器人展区"})
        self.assertEqual(result["code"], "ROBOT_BUSY")
        self.assertEqual(get_robot_status()["data"]["current_area"], "入口")

    def test_timeout_blocks_repeated_model_action(self):
        reset_robot("timeout")
        self.assertEqual(execute_tool("navigate_to", {"area": "机器人展区"})["code"], "TIMEOUT")
        self.assertEqual(execute_tool("navigate_to", {"area": "机器人展区"})["code"], "STATE_UNKNOWN")

    def test_reset_tool_not_available(self):
        self.assertEqual(execute_tool("reset_robot", {})["code"], "UNKNOWN_TOOL")

    def test_invalid_args_do_not_move_robot(self):
        self.assertEqual(execute_tool("navigate_to", {})["code"], "INVALID_ARGUMENT")
        self.assertEqual(get_robot_status()["data"]["current_area"], "入口")

    def test_model_round_limit(self):
        fake = FakeModel([call("get_robot_status"), call("get_robot_status", index=2)])
        agent = ShowroomAgent(fake, max_rounds=2)
        with self.assertRaises(AgentLimitError):
            agent.ask("一直查询")
        self.assertEqual(len(fake.requests), 2)
        self.assertEqual(len(agent.messages), 1)

    def test_tool_limit_prevents_new_action(self):
        fake = FakeModel([call("navigate_to", {"area": "工业展区"})])
        with self.assertRaises(AgentLimitError):
            ShowroomAgent(fake, max_tools=0).ask("带路")
        self.assertEqual(get_robot_status()["data"]["current_area"], "入口")

    def test_api_failure_does_not_undo_completed_action(self):
        fake = FakeModel([call("navigate_to", {"area": "工业展区"}), RuntimeError("network")])
        agent = ShowroomAgent(fake)
        with self.assertRaises(RuntimeError):
            agent.ask("带路")
        self.assertEqual(get_robot_status()["data"]["current_area"], "工业展区")
        self.assertEqual(len(agent.messages), 1)

    def test_multiturn_followup_includes_prior_question(self):
        fake = FakeModel([AIMessage(content="去哪个展区？"), AIMessage(content="收到")])
        agent = ShowroomAgent(fake)
        agent.ask("带我过去")
        agent.ask("工业展区")
        self.assertEqual([m.content for m in fake.requests[1]][-3:], ["带我过去", "去哪个展区？", "工业展区"])

    def test_config_and_errors_do_not_expose_key(self):
        key = "sk-example-secret-for-test"
        self.assertNotIn(key, repr(ModelConfig(key, "https://example.com", "example")))
        self.assertNotIn(key, friendly_error(RuntimeError(key)))

    def test_reject_non_aliyun_endpoint(self):
        with patch("model_config.dotenv_values", return_value={
            "DASHSCOPE_API_KEY": "sk-example", "DASHSCOPE_BASE_URL": "https://example.com/compatible-mode/v1",
            "DASHSCOPE_MODEL": "example",
        }):
            with self.assertRaises(ValueError):
                load_config()


if __name__ == "__main__":
    unittest.main()
