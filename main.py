"""运行入口：菜单练习或 --demo 自动演示。"""

import argparse
import json

from robot_tools import (
    AREAS,
    SCENARIOS,
    get_robot_status,
    navigate_to,
    reset_robot,
    search_product_info,
)


def show(label, result):
    print(f"\n【{label}】")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_demo(scenario):
    reset_robot(scenario)
    show("导航前", get_robot_status())
    navigation = navigate_to("机器人展区")
    show("导航结果", navigation)
    show("导航后", get_robot_status())
    if navigation["success"]:
        show("资料检索", search_product_info("导览机器人A"))
    else:
        print("\n导航未确认成功，本次组合演示到此结束。")


def run_menu(scenario):
    reset_robot(scenario)
    while True:
        print("\n1 查询状态  2 模拟导航  3 检索资料  4 重置/切换场景  0 退出")
        try:
            choice = input("请选择：").strip()
            if choice == "0":
                return
            if choice == "1":
                show("状态", get_robot_status())
            elif choice == "2":
                print("可选展区：" + "、".join(AREAS))
                show("导航", navigate_to(input("目标展区：")))
            elif choice == "3":
                show("检索", search_product_info(input("产品名/展区/功能关键词：")))
            elif choice == "4":
                print("normal 正常 / busy 忙碌 / offline 离线 / navigation_failure 失败 / timeout 超时")
                selected = input("输入场景英文名称：").strip()
                if selected in SCENARIOS:
                    reset_robot(selected)
                    show("环境已重置", get_robot_status())
                else:
                    print("场景名称无效，环境保持原样。")
            else:
                print("请输入 0 到 4。")
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return


def main():
    parser = argparse.ArgumentParser(description="机器人展厅助手：本地工具练习")
    parser.add_argument("--demo", action="store_true", help="执行一次自动演示")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal", help="模拟场景")
    args = parser.parse_args()
    print("机器人展厅助手 · 第一阶段：本地工具（尚未接入大模型和真实机器人）")
    if args.demo:
        run_demo(args.scenario)
    else:
        run_menu(args.scenario)


if __name__ == "__main__":
    main()
