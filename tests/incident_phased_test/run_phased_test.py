"""
分阶段回测脚本

用法：
    python tests/incident_phased_test/run_phased_test.py [--base-url http://localhost:5001] [--phase N]

流程：
    Phase 0: 创建新项目
    Phase 1-4: 每个阶段依次执行：
        1) 追加该阶段材料
        2) 重建基线（LLM 自动分析）
        3) 打印基线摘要
        4) 打印"系统认为接下来会发生什么"（基于 current_risks + monitoring_signals）
        5) 打印"实际接下来发生了什么"（对照信息）

    用户可以选择逐阶段手动推进，也可以一次性跑完。
"""

import argparse
import json
import os
import sys
import time
import requests

# 导入阶段数据
sys.path.insert(0, os.path.dirname(__file__))
from phases import PHASES


def log(msg, color=None):
    colors = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "cyan": "\033[96m", "bold": "\033[1m"}
    reset = "\033[0m"
    prefix = colors.get(color, "") if color else ""
    print(f"{prefix}{msg}{reset if prefix else ''}")


def api(method, url, base_url, **kwargs):
    full_url = f"{base_url}{url}"
    kwargs.setdefault("timeout", 120)
    resp = getattr(requests, method)(full_url, **kwargs)
    data = resp.json()
    if not data.get("success"):
        log(f"  API ERROR: {data.get('error', 'unknown')}", "red")
    return data


def create_project(base_url):
    """创建一个新的测试项目"""
    log("\n" + "=" * 70, "bold")
    log("Phase 0: 创建测试项目", "bold")
    log("=" * 70, "bold")

    resp = api("post", "/api/incident/project/create", base_url, json={
        "name": "【回测】华中农大研究生举报导师事件",
        "simulation_requirement": "华中农业大学11名研究生联名举报导师黄某某学术不端和师德失范，分析事件演化走势及处置建议",
    })

    if resp.get("success"):
        project_id = resp["data"]["project_id"]
        log(f"  项目创建成功: {project_id}", "green")
        return project_id
    else:
        log(f"  项目创建失败: {resp.get('error')}", "red")
        return None


def run_phase(base_url, project_id, phase, prev_baseline_id=None):
    """执行一个阶段的测试"""
    p = phase
    phase_num = p["phase_id"]

    log(f"\n{'=' * 70}", "bold")
    log(f"Phase {phase_num}: {p['phase_name']}（{p['time_label']}）", "bold")
    log(f"{'=' * 70}", "bold")

    # ── Step 1: 追加材料 ──
    log(f"\n  [1/3] 追加材料: {p['title']}")
    resp = api("post", f"/api/incident/project/{project_id}/materials/append", base_url,
               json={"title": p["title"], "text": p["text"], "source_type": "manual"})

    if resp.get("success"):
        mat_ids = resp["data"].get("material_ids", [])
        log(f"        材料已追加: {len(mat_ids)} 条", "green")
    else:
        log(f"        材料追加失败", "red")
        return None

    # ── Step 2: 重建基线 ──
    log(f"  [2/3] 重建基线（LLM 分析中，可能需要 30-60 秒）...")
    start = time.time()
    resp = api("post", f"/api/incident/project/{project_id}/baseline/rebuild", base_url, json={})
    elapsed = time.time() - start
    log(f"        基线重建耗时: {elapsed:.1f}s")

    if not resp.get("success"):
        log(f"        基线重建失败", "red")
        return None

    bl = resp["data"]
    baseline_id = bl["baseline_id"]

    # ── Step 3: 打印基线摘要 ──
    log(f"\n  [3/3] 基线摘要 ({baseline_id})", "cyan")
    log(f"        阶段判断: {bl.get('current_stage', '未知')}", "cyan")

    log(f"\n        ── 已确认事实 ({len(bl.get('confirmed_facts', []))}) ──")
    for i, fact in enumerate(bl.get("confirmed_facts", [])[:8], 1):
        log(f"          {i}. {fact}")

    log(f"\n        ── 关键主体 ({len(bl.get('key_actors', []))}) ──")
    actors = bl.get("key_actors", [])
    log(f"          {', '.join(actors[:10])}")

    log(f"\n        ── 当前风险 ({len(bl.get('current_risks', []))}) ──")
    for i, risk in enumerate(bl.get("current_risks", [])[:5], 1):
        log(f"          {i}. {risk}", "yellow")

    log(f"\n        ── 待解答问题 ({len(bl.get('open_questions', []))}) ──")
    for i, q in enumerate(bl.get("open_questions", [])[:5], 1):
        log(f"          {i}. {q}")

    log(f"\n        ── 建议监测信号 ({len(bl.get('recommended_monitoring_signals', []))}) ──")
    for i, s in enumerate(bl.get("recommended_monitoring_signals", [])[:5], 1):
        log(f"          {i}. {s}")

    # ── 基线 diff（从第2阶段起） ──
    if prev_baseline_id:
        log(f"\n        ── 基线变化 (vs 上一版本) ──")
        resp_diff = api("post", f"/api/incident/project/{project_id}/baseline/diff", base_url,
                        json={"baseline_a_id": prev_baseline_id, "baseline_b_id": baseline_id})
        if resp_diff.get("success"):
            diff = resp_diff["data"]
            stage_change = diff.get("stage_change", {})
            if stage_change.get("before") != stage_change.get("after"):
                log(f"          阶段变化: {stage_change.get('before')} → {stage_change.get('after')}", "yellow")
            facts_diff = diff.get("confirmed_facts_diff", {})
            added = facts_diff.get("added", [])
            if added:
                log(f"          新增事实: {len(added)} 条")
                for f in added[:3]:
                    log(f"            + {f[:60]}...")

    # ── 对照真实后续 ──
    log(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    log(f"  ║ 系统预测的风险/信号 vs 实际接下来发生的事", "bold")
    log(f"  ╠══════════════════════════════════════════════════════════════╣")
    log(f"  ║ 【系统认为的关键风险】")
    for risk in bl.get("current_risks", [])[:3]:
        log(f"  ║   ⚠ {risk[:55]}", "yellow")
    log(f"  ║")
    log(f"  ║ 【实际接下来发生了什么】")
    for item in p.get("reality_next", []):
        log(f"  ║   ✓ {item}", "green")
    log(f"  ╚══════════════════════════════════════════════════════════════╝")

    return baseline_id


def main():
    parser = argparse.ArgumentParser(description="事件工作台分阶段回测")
    parser.add_argument("--base-url", default="http://localhost:5001", help="后端 API 地址")
    parser.add_argument("--project-id", default=None, help="使用已有项目 ID（跳过创建）")
    parser.add_argument("--phase", type=int, default=None, help="只运行指定阶段（1-4）")
    parser.add_argument("--auto", action="store_true", help="自动运行所有阶段，不暂停")
    args = parser.parse_args()

    log("╔══════════════════════════════════════════════════════════════════╗", "bold")
    log("║      NexusMind 事件工作台 · 分阶段回测                         ║", "bold")
    log("║      案例: 华中农大11名研究生联名举报导师事件                    ║", "bold")
    log("╚══════════════════════════════════════════════════════════════════╝", "bold")

    # 创建或使用已有项目
    if args.project_id:
        project_id = args.project_id
        log(f"\n使用已有项目: {project_id}")
    else:
        project_id = create_project(args.base_url)
        if not project_id:
            log("项目创建失败，退出", "red")
            return

    # 运行各阶段
    prev_baseline_id = None
    phases_to_run = PHASES if args.phase is None else [p for p in PHASES if p["phase_id"] == args.phase]

    for phase in phases_to_run:
        if not args.auto and phase["phase_id"] > 1:
            log(f"\n{'─' * 50}")
            log(f"  上方是 Phase {phase['phase_id'] - 1} 的系统分析结果。")
            log(f"  请对比【系统预测的风险/信号】和【实际发生的事】。")
            log(f"  准备好后按 Enter 继续喂入 Phase {phase['phase_id']} 的材料...")
            input()

        prev_baseline_id = run_phase(args.base_url, project_id, phase, prev_baseline_id)
        if prev_baseline_id is None:
            log("阶段执行失败，终止", "red")
            break

    log(f"\n{'=' * 70}", "bold")
    log("回测完成！", "bold")
    log(f"项目 ID: {project_id}", "cyan")
    log(f"浏览器查看: http://localhost:3000/incident/{project_id}", "cyan")
    log(f"{'=' * 70}", "bold")


if __name__ == "__main__":
    main()
