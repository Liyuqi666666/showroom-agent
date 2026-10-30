"""第一阶段：三个可直接调用的 Python 工具，全部在本地模拟运行。

先阅读 get_robot_status、navigate_to、search_product_info 三个函数。
这里没有调用大模型，也没有连接真实机器人；检索使用关键词匹配。
"""

import json
from pathlib import Path
import re


AREAS = ("机器人展区", "工业展区", "互动展区")
SCENARIOS = ("normal", "busy", "offline", "navigation_failure", "timeout")
KNOWLEDGE_PATH = Path(__file__).parent / "knowledge" / "products.json"

_robot_state = {}
_scenario = "normal"


def _result(success, code, message, data=None):
    """统一返回格式，方便以后接入模型或 HTTP 接口。"""
    return {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "simulation": True,
    }


def reset_robot(scenario="normal"):
    """重置练习环境。仅供演示和测试使用，不作为 Agent 的动作工具。"""
    global _scenario
    if scenario not in SCENARIOS:
        raise ValueError(f"未知场景：{scenario}，可选：{SCENARIOS}")
    _scenario = scenario
    status = {"busy": "busy", "offline": "offline"}.get(scenario, "idle")
    _robot_state.clear()
    _robot_state.update({
        "status": status,
        "current_area": "入口",
        "battery_percent": 85,
        "position_confirmed": True,
    })


def get_robot_status():
    """查询模拟机器人状态、位置和电量；不修改状态。"""
    # 返回副本，避免调用方意外修改内部状态。
    return _result(True, "OK", "已读取模拟机器人状态", dict(_robot_state))


def navigate_to(area: str):
    """模拟导航到指定展区。

    area 必须为：机器人展区、工业展区、互动展区。
    忙碌、离线或状态未知时拒绝动作。只有成功才更新位置。
    第一版同步返回最终结果，后续可替换为真实机器人的动作 API。
    """
    if not isinstance(area, str) or not area.strip():
        return _result(False, "INVALID_ARGUMENT", "请提供展区名称")
    area = area.strip()
    if area not in AREAS:
        return _result(False, "UNKNOWN_AREA", "目的地不存在", {"available_areas": list(AREAS)})

    status = _robot_state["status"]
    if status != "idle":
        messages = {
            "busy": ("ROBOT_BUSY", "机器人正在忙，请稍后再试"),
            "offline": ("ROBOT_OFFLINE", "机器人离线，无法导航"),
            "unknown": ("STATE_UNKNOWN", "上次执行结果未知，请确认状态后再操作"),
        }
        code, message = messages.get(status, ("STATE_UNKNOWN", "机器人状态异常"))
        return _result(False, code, message, dict(_robot_state))

    if _robot_state["current_area"] == area:
        return _result(True, "ALREADY_THERE", "模拟机器人已在目标展区，无需重复导航", dict(_robot_state))

    if _scenario == "navigation_failure":
        return _result(False, "NAVIGATION_FAILED", "模拟导航失败：路线不可达", dict(_robot_state))

    if _scenario == "timeout":
        # 这是可控故障注入，不会真正等待网络超时。
        # 超时不代表动作一定未执行，因此位置标记为未确认，阻止重复导航。
        _robot_state["status"] = "unknown"
        _robot_state["position_confirmed"] = False
        return _result(False, "TIMEOUT", "模拟接口超时，导航结果未知；current_area 为最后确认的位置", dict(_robot_state))

    _robot_state["current_area"] = area
    return _result(True, "OK", "模拟导航完成", dict(_robot_state))


def _normalize(text):
    return re.sub(r"[\s，。！？、,.!?：:；;]", "", text).casefold()


def search_product_info(query: str):
    """按产品名、别名、展区或功能关键词检索本地资料。

    返回匹配的原始资料及可定位的来源。没有结果时返回空列表。
    第一版是关键词检索，不具备向量检索或大模型语义理解能力。
    """
    if not isinstance(query, str) or not _normalize(query):
        return _result(False, "INVALID_ARGUMENT", "请输入产品名、展区或功能关键词")

    try:
        products = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
        required = {"id", "name", "area", "description", "capabilities", "limitations", "aliases"}
        if not isinstance(products, list) or any(
            not isinstance(p, dict) or not required.issubset(p)
            or not all(isinstance(p[k], str) for k in ("id", "name", "area", "description", "limitations"))
            or not all(isinstance(p[k], list) and all(isinstance(v, str) for v in p[k]) for k in ("aliases", "capabilities"))
            for p in products
        ):
            raise ValueError("资料格式不符合约定")
    except (OSError, ValueError):
        return _result(False, "KNOWLEDGE_ERROR", "产品资料无法读取，请检查 knowledge/products.json")

    normalized = _normalize(query)
    matches = []
    for product in products:
        terms = [product["name"], product["area"], *product["aliases"], *product["capabilities"]]
        if any(term and (term in normalized or normalized in term) for term in map(_normalize, terms)):
            matches.append({
                **product,
                "source": f"knowledge/products.json#{product['id']}",
                "fictional": True,
            })

    message = f"找到 {len(matches)} 条虚构练习资料" if matches else "未找到匹配资料，请尝试产品名、展区或功能关键词"
    return _result(True, "OK", message, {"total": len(matches), "products": matches})


reset_robot()
