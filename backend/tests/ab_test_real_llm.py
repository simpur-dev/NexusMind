"""
真实 LLM A/B 对比测试：世界模型反馈闭环

运行方式：
  cd backend
  uv run python tests/ab_test_real_llm.py

原理：
  1. 创建一个精简的模拟配置（5 个 Agent, 3 轮, Twitter-only）
  2. A 组：使用 --no-world-model 运行，Agent 不感知环境状态
  3. B 组：正常运行，Agent 感知环境状态
  4. 对比两组的动作日志（发帖内容、情感倾向、行为多样性）
  
预计耗时：约 3-5 分钟（取决于 LLM 响应速度）
预计 API 调用：约 30 次（5 Agent × 3 轮 × 2 组）
"""

import os
import sys
import json
import time
import shutil
import subprocess
import tempfile
from datetime import datetime
from collections import Counter
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# 精简配置生成
# ============================================================

def create_ab_test_config(output_dir: str, simulation_id: str) -> str:
    """创建精简的 A/B 测试模拟配置"""
    
    config = {
        "simulation_id": simulation_id,
        "project_id": "ab_test",
        "graph_id": "ab_test_graph",
        "simulation_requirement": "武汉大学撤销某学生纪律处分后，公众舆论走向",
        "time_config": {
            "total_simulation_hours": 3,
            "minutes_per_round": 60,
            "agents_per_hour_min": 3,
            "agents_per_hour_max": 5,
            "peak_hours": [19, 20, 21],
            "peak_activity_multiplier": 1.5,
            "off_peak_hours": [],
            "off_peak_activity_multiplier": 1.0,
            "morning_hours": [],
            "morning_activity_multiplier": 1.0,
            "work_hours": [],
            "work_activity_multiplier": 1.0,
        },
        "agent_configs": [
            {
                "agent_id": 0,
                "entity_uuid": "ab-test-001",
                "entity_name": "武汉大学",
                "entity_type": "University",
                "activity_level": 0.8,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.0,
                "active_hours": [0, 1, 2],
                "response_delay_min": 1,
                "response_delay_max": 5,
                "sentiment_bias": 0.3,
                "stance": "neutral",
                "influence_weight": 1.5,
            },
            {
                "agent_id": 1,
                "entity_uuid": "ab-test-002",
                "entity_name": "在校学生",
                "entity_type": "Student",
                "activity_level": 0.9,
                "posts_per_hour": 1.5,
                "comments_per_hour": 3.0,
                "active_hours": [0, 1, 2],
                "response_delay_min": 1,
                "response_delay_max": 5,
                "sentiment_bias": -0.6,
                "stance": "opposing",
                "influence_weight": 1.0,
            },
            {
                "agent_id": 2,
                "entity_uuid": "ab-test-003",
                "entity_name": "校友",
                "entity_type": "Alumni",
                "activity_level": 0.7,
                "posts_per_hour": 0.8,
                "comments_per_hour": 2.0,
                "active_hours": [0, 1, 2],
                "response_delay_min": 1,
                "response_delay_max": 5,
                "sentiment_bias": -0.3,
                "stance": "opposing",
                "influence_weight": 1.2,
            },
            {
                "agent_id": 3,
                "entity_uuid": "ab-test-004",
                "entity_name": "记者",
                "entity_type": "Journalist",
                "activity_level": 0.6,
                "posts_per_hour": 0.3,
                "comments_per_hour": 1.0,
                "active_hours": [0, 1, 2],
                "response_delay_min": 1,
                "response_delay_max": 5,
                "sentiment_bias": -0.1,
                "stance": "neutral",
                "influence_weight": 1.3,
            },
            {
                "agent_id": 4,
                "entity_uuid": "ab-test-005",
                "entity_name": "普通网民",
                "entity_type": "Person",
                "activity_level": 0.8,
                "posts_per_hour": 1.0,
                "comments_per_hour": 2.0,
                "active_hours": [0, 1, 2],
                "response_delay_min": 1,
                "response_delay_max": 5,
                "sentiment_bias": -0.4,
                "stance": "opposing",
                "influence_weight": 0.8,
            },
        ],
        "event_config": {
            "initial_posts": [
                {
                    "content": "经学校纪律审查委员会复核，决定撤销此前对某同学作出的处分决定。学校始终坚持实事求是、有错必纠的原则。",
                    "poster_type": "University",
                    "poster_agent_id": 0,
                },
            ],
            "scheduled_events": [],
            "hot_topics": ["武大撤销处分", "程序正义", "高校治理"],
            "narrative_direction": "舆论从个案关注升维为对武汉大学治理能力的质疑",
        },
        "platforms": {
            "twitter": {"enabled": True},
            "reddit": {"enabled": False},
        },
    }
    
    # 生成 profile 文件（OASIS Twitter CSV: user_id, name, username, user_char, description）
    persona_map = {
        "武汉大学": "你是武汉大学官方社交媒体账号。你代表学校立场，发布官方声明和政策解读。你的语气正式、权威，强调学校的纠错诚意和改革决心。你避免情绪化表达。",
        "在校学生": "你是武汉大学在读本科生。你对学校的纪律处分程序深感不满，认为学校缺乏透明度和程序正义。你的表达直接、情绪化，经常使用反问和质疑。你关心自身权益。",
        "校友": "你是武汉大学2015级校友，现在在互联网公司工作。你对母校有感情但也有失望。你的观点理性但带有批判性，关注学校治理的长期影响。你会引用具体案例来支持观点。",
        "记者": "你是一名教育领域记者。你关注高校治理和学术公正问题。你的报道客观中立，注重事实核查，会采访多方观点。你会追问细节和背后的制度问题。",
        "普通网民": "你是一名关注社会热点的普通网民。你对高校丑闻比较敏感，容易被情绪化内容感染。你的发言简短、口语化，有时会跟风转发或发表吐槽。",
    }
    
    profiles = []
    for ac in config["agent_configs"]:
        name = ac["entity_name"]
        profiles.append({
            "user_id": ac["agent_id"],
            "name": name,
            "username": name.replace(" ", "_"),
            "user_char": persona_map.get(name, f"你是{name}，对武汉大学事件有自己的看法。"),
            "description": f"{name} - 关注高校治理与学术公正",
        })
    
    config_path = os.path.join(output_dir, "simulation_config.json")
    profile_path = os.path.join(output_dir, "twitter_profiles.csv")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # CSV profile（OASIS 通过 pandas 读取，列顺序：user_id, name, username, user_char, description）
    import csv
    with open(profile_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "name", "username", "user_char", "description"])
        for p in profiles:
            writer.writerow([p["user_id"], p["name"], p["username"], p["user_char"], p["description"]])
    
    return config_path


# ============================================================
# 模拟运行
# ============================================================

def run_simulation(config_path: str, label: str, no_world_model: bool = False, max_rounds: int = 3) -> Dict:
    """运行一次模拟并返回结果"""
    
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    script = os.path.join(scripts_dir, 'run_parallel_simulation.py')
    sim_dir = os.path.dirname(config_path)
    
    cmd = [
        sys.executable, script,
        "--config", config_path,
        "--twitter-only",
        "--max-rounds", str(max_rounds),
        "--no-wait",
    ]
    if no_world_model:
        cmd.append("--no-world-model")
    
    # 设置环境
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    print(f"\n{'='*60}")
    print(f"运行 {label} 组...")
    print(f"  命令: {' '.join(cmd[-5:])}")
    print(f"  世界模型: {'禁用' if no_world_model else '启用'}")
    print(f"{'='*60}")
    
    start = time.time()
    result = subprocess.run(
        cmd, cwd=sim_dir, env=env,
        capture_output=True, text=True, encoding='utf-8',
        timeout=300,
    )
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"  ⚠️ 进程退出码: {result.returncode}")
        # 打印最后 20 行输出
        lines = (result.stdout or "").strip().split("\n")
        for line in lines[-20:]:
            print(f"    | {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-10:]:
                print(f"    ERR| {line}")
        return {"error": True, "elapsed": elapsed}
    
    print(f"  ✅ 完成，耗时 {elapsed:.1f}s")
    
    # 读取动作日志
    actions_path = os.path.join(sim_dir, "twitter", "actions.jsonl")
    actions = []
    if os.path.exists(actions_path):
        with open(actions_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        actions.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    
    # 读取世界状态文件（如果有的话）
    ws_path = os.path.join(sim_dir, "world_state_current.json")
    world_state = None
    if os.path.exists(ws_path):
        with open(ws_path, 'r', encoding='utf-8') as f:
            world_state = json.load(f)
    
    return {
        "error": False,
        "elapsed": elapsed,
        "actions": actions,
        "world_state": world_state,
        "stdout": result.stdout,
    }


# ============================================================
# 分析对比
# ============================================================

def analyze_actions(actions: List[Dict]) -> Dict:
    """分析动作日志"""
    if not actions:
        return {"total": 0, "action_types": {}, "all_texts": [], "post_count": 0,
                "neg_ratio": 0, "pos_ratio": 0, "avg_content_length": 0,
                "unique_agents": 0, "sample_posts": []}
    
    # 过滤出实际动作（排除 round_start/round_end 等元数据）
    real_actions = [a for a in actions if a.get("action_type") and a["action_type"] not in ("round_start", "round_end", "simulation_start", "simulation_end")]
    
    action_types = Counter(a.get("action_type", "unknown") for a in real_actions)
    unique_agents = len(set(a.get("agent_id") for a in real_actions if a.get("agent_id") is not None))
    
    # 提取所有原创文本（帖子 + quote 中的原创评论）
    all_texts = []
    for a in real_actions:
        args = a.get("action_args", {})
        # CREATE_POST 内容
        if a.get("action_type") in ("create_post", "CREATE_POST"):
            content = args.get("content", "")
            if content:
                all_texts.append({"agent": a.get("agent_name", "?"), "type": "post", "text": content})
        # CREATE_COMMENT 内容
        elif a.get("action_type") in ("create_comment", "CREATE_COMMENT"):
            content = args.get("content", "")
            if content:
                all_texts.append({"agent": a.get("agent_name", "?"), "type": "comment", "text": content})
        # QUOTE_POST 中的 quote_content（Agent 原创观点）
        elif a.get("action_type") in ("quote_post", "QUOTE_POST"):
            qc = args.get("quote_content", "")
            if qc:
                all_texts.append({"agent": a.get("agent_name", "?"), "type": "quote", "text": qc})
    
    # 简单情感分析（在所有原创文本上）
    neg_keywords = ["愤怒", "失望", "不满", "质疑", "批评", "反对", "抗议", "黑幕", "腐败", 
                     "不公", "虚假", "恐慌", "危机", "无门", "不透明", "敷衍", "遮羞布", 
                     "申辩", "问责", "缺乏", "哪里"]
    pos_keywords = ["支持", "肯定", "改善", "进步", "信任", "期待", "有错必纠", "理性", 
                     "建设", "积极", "保障", "优化", "欣慰", "重视", "完善"]
    
    neg_count = 0
    pos_count = 0
    for item in all_texts:
        text = item["text"]
        is_neg = any(kw in text for kw in neg_keywords)
        is_pos = any(kw in text for kw in pos_keywords)
        if is_neg:
            neg_count += 1
        if is_pos:
            pos_count += 1
    
    total_texts = len(all_texts) or 1
    avg_length = sum(len(t["text"]) for t in all_texts) / total_texts if all_texts else 0
    
    # 按 agent 统计发言分布
    agent_text_count = Counter(t["agent"] for t in all_texts)
    
    return {
        "total": len(real_actions),
        "action_types": dict(action_types),
        "all_texts": all_texts,
        "post_count": len(all_texts),
        "neg_ratio": neg_count / total_texts,
        "pos_ratio": pos_count / total_texts,
        "avg_content_length": avg_length,
        "unique_agents": unique_agents,
        "agent_text_count": dict(agent_text_count),
        "sample_posts": [t["text"] for t in all_texts[:5]],
    }


def main():
    print("=" * 70)
    print("真实 LLM A/B 对比测试：世界模型反馈闭环")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"配置: 5 个 Agent, 5 轮, Twitter-only")
    print(f"A组: 无世界模型反馈")
    print(f"B组: 有世界模型反馈")
    print()
    
    # 创建临时目录
    base_dir = tempfile.mkdtemp(prefix="nexusmind_ab_")
    dir_a = os.path.join(base_dir, "group_A")
    dir_b = os.path.join(base_dir, "group_B")
    os.makedirs(dir_a, exist_ok=True)
    os.makedirs(dir_b, exist_ok=True)
    os.makedirs(os.path.join(dir_a, "twitter"), exist_ok=True)
    os.makedirs(os.path.join(dir_b, "twitter"), exist_ok=True)
    
    print(f"工作目录: {base_dir}")
    
    # 生成配置
    config_a = create_ab_test_config(dir_a, "ab_test_A")
    config_b = create_ab_test_config(dir_b, "ab_test_B")
    
    MAX_ROUNDS = 5
    
    # 运行 A 组（无世界模型）
    result_a = run_simulation(config_a, "A（无世界模型）", no_world_model=True, max_rounds=MAX_ROUNDS)
    
    # B 组：预写世界状态文件（模拟后端 _monitor_simulation 线程的行为）
    # 场景：第2轮后环境已高恐慌、低信任，验证 Agent 是否改变行为
    from app.services.world_state import WorldStateSnapshot
    ws_seed = WorldStateSnapshot(
        round_num=2, timestamp=datetime.now().isoformat(),
        attention_level=0.75,       # 高关注
        panic_level=0.65,           # 较高恐慌
        trust_level=0.25,           # 低信任
        polarization_level=0.55,    # 中高极化
        risk_level=0.6,             # 较高风险
        stability_level=0.3,        # 低稳定性
    )
    ws_payload = ws_seed.to_dict()
    ws_payload["state_summary_text"] = ws_seed.get_state_summary_text()
    ws_payload["recent_events"] = [
        {"event_type": "heat_spike", "description": "舆论热度急剧上升，多个平台出现大量讨论", "severity": 0.8},
        {"event_type": "trust_drop", "description": "公众对校方声明的信任度显著下降", "severity": 0.7},
    ]
    ws_file_b = os.path.join(dir_b, "world_state_current.json")
    with open(ws_file_b, 'w', encoding='utf-8') as f:
        json.dump(ws_payload, f, ensure_ascii=False, indent=2)
    print(f"已预写世界状态文件: {ws_file_b}")
    print(f"  场景: 恐慌={ws_seed.panic_level}, 信任={ws_seed.trust_level}, 极化={ws_seed.polarization_level}")
    
    # 运行 B 组（有世界模型）
    result_b = run_simulation(config_b, "B（有世界模型）", no_world_model=False, max_rounds=MAX_ROUNDS)
    
    # 分析
    if result_a.get("error") or result_b.get("error"):
        print("\n⚠️ 有一组模拟失败，无法对比")
        if result_a.get("error"):
            print("  A组失败")
        if result_b.get("error"):
            print("  B组失败")
        return
    
    analysis_a = analyze_actions(result_a["actions"])
    analysis_b = analyze_actions(result_b["actions"])
    
    # 输出对比
    print("\n" + "=" * 70)
    print("对比结果")
    print("=" * 70)
    
    print(f"\n{'指标':<25} {'A组(无世界模型)':<20} {'B组(有世界模型)':<20}")
    print("-" * 65)
    print(f"{'总动作数':<25} {analysis_a['total']:<20} {analysis_b['total']:<20}")
    print(f"{'原创文本数':<23} {analysis_a['post_count']:<20} {analysis_b['post_count']:<20}")
    print(f"{'活跃Agent数':<22} {analysis_a['unique_agents']:<20} {analysis_b['unique_agents']:<20}")
    print(f"{'负面内容占比':<22} {analysis_a['neg_ratio']:<20.2%} {analysis_b['neg_ratio']:<20.2%}")
    print(f"{'正面内容占比':<22} {analysis_a['pos_ratio']:<20.2%} {analysis_b['pos_ratio']:<20.2%}")
    print(f"{'平均内容长度(字)':<20} {analysis_a['avg_content_length']:<20.0f} {analysis_b['avg_content_length']:<20.0f}")
    print(f"{'运行耗时(秒)':<22} {result_a['elapsed']:<20.1f} {result_b['elapsed']:<20.1f}")
    
    # 动作类型分布
    print(f"\n动作类型分布:")
    all_types = set(list(analysis_a.get("action_types", {}).keys()) + list(analysis_b.get("action_types", {}).keys()))
    for at in sorted(all_types):
        ca = analysis_a.get("action_types", {}).get(at, 0)
        cb = analysis_b.get("action_types", {}).get(at, 0)
        print(f"  {at:<25} {ca:<20} {cb:<20}")
    
    # 各 Agent 发言分布
    print(f"\n各 Agent 原创文本数:")
    all_agents = set(list(analysis_a.get("agent_text_count", {}).keys()) + list(analysis_b.get("agent_text_count", {}).keys()))
    for ag in sorted(all_agents):
        ca = analysis_a.get("agent_text_count", {}).get(ag, 0)
        cb = analysis_b.get("agent_text_count", {}).get(ag, 0)
        print(f"  {ag:<25} {ca:<20} {cb:<20}")
    
    # 全部原创文本对比
    print(f"\n{'='*70}")
    print("A组 全部原创文本:")
    print("-" * 70)
    for i, item in enumerate(analysis_a.get("all_texts", [])):
        print(f"  [{item['agent']}] ({item['type']}) {item['text'][:120]}{'...' if len(item['text'])>120 else ''}")
    
    print(f"\nB组 全部原创文本:")
    print("-" * 70)
    for i, item in enumerate(analysis_b.get("all_texts", [])):
        print(f"  [{item['agent']}] ({item['type']}) {item['text'][:120]}{'...' if len(item['text'])>120 else ''}")
    
    # 世界状态（只有 B 组有）
    if result_b.get("world_state"):
        ws = result_b["world_state"]
        print(f"\nB组最终世界状态:")
        for key in ["attention_level", "panic_level", "trust_level", "polarization_level", "risk_level", "stability_level"]:
            print(f"  {key}: {ws.get(key, 'N/A')}")
    
    # 评分
    print(f"\n{'='*70}")
    print("评分")
    print("-" * 70)
    score_a, score_b = 0, 0
    
    checks = []
    
    # 1. 行为多样性（动作类型数量）
    type_a = len(analysis_a.get("action_types", {}))
    type_b = len(analysis_b.get("action_types", {}))
    if type_b > type_a:
        checks.append(("行为多样性(动作类型数)", "B", f"A={type_a}, B={type_b}"))
        score_b += 1
    elif type_a > type_b:
        checks.append(("行为多样性(动作类型数)", "A", f"A={type_a}, B={type_b}"))
        score_a += 1
    else:
        checks.append(("行为多样性(动作类型数)", "-", f"A={type_a}, B={type_b}"))
    
    # 2. 内容丰富度
    if analysis_b["avg_content_length"] > analysis_a["avg_content_length"] + 5:
        checks.append(("内容丰富度(平均长度)", "B", f"A={analysis_a['avg_content_length']:.0f}, B={analysis_b['avg_content_length']:.0f}"))
        score_b += 1
    elif analysis_a["avg_content_length"] > analysis_b["avg_content_length"] + 5:
        checks.append(("内容丰富度(平均长度)", "A", f"A={analysis_a['avg_content_length']:.0f}, B={analysis_b['avg_content_length']:.0f}"))
        score_a += 1
    else:
        checks.append(("内容丰富度(平均长度)", "-", f"A={analysis_a['avg_content_length']:.0f}, B={analysis_b['avg_content_length']:.0f}"))
    
    # 3. 参与度（活跃agent数）
    if analysis_b["unique_agents"] > analysis_a["unique_agents"]:
        checks.append(("参与广度(活跃Agent)", "B", f"A={analysis_a['unique_agents']}, B={analysis_b['unique_agents']}"))
        score_b += 1
    elif analysis_a["unique_agents"] > analysis_b["unique_agents"]:
        checks.append(("参与广度(活跃Agent)", "A", f"A={analysis_a['unique_agents']}, B={analysis_b['unique_agents']}"))
        score_a += 1
    else:
        checks.append(("参与广度(活跃Agent)", "-", f"A={analysis_a['unique_agents']}, B={analysis_b['unique_agents']}"))
    
    # 4. 原创文本数
    if analysis_b["post_count"] > analysis_a["post_count"]:
        checks.append(("原创文本总量", "B", f"A={analysis_a['post_count']}, B={analysis_b['post_count']}"))
        score_b += 1
    elif analysis_a["post_count"] > analysis_b["post_count"]:
        checks.append(("原创文本总量", "A", f"A={analysis_a['post_count']}, B={analysis_b['post_count']}"))
        score_a += 1
    else:
        checks.append(("原创文本总量", "-", f"A={analysis_a['post_count']}, B={analysis_b['post_count']}"))
    
    for label, winner, detail in checks:
        icon = "✅B" if winner == "B" else ("✅A" if winner == "A" else "  -")
        print(f"  {icon} {label}: {detail}")
    
    print(f"\n综合: A胜 {score_a} 项, B胜 {score_b} 项")
    if score_b > score_a:
        print("✅ 世界模型在真实LLM模拟中表现更优")
    elif score_a > score_b:
        print("⚠️  世界模型在真实LLM模拟中未表现出优势")
    else:
        print("➡️  两组表现相当（样本量小，需更多轮次才能定论）")
    
    print(f"\n📁 完整数据保存在: {base_dir}")
    print(f"   A组: {os.path.join(dir_a, 'twitter', 'actions.jsonl')}")
    print(f"   B组: {os.path.join(dir_b, 'twitter', 'actions.jsonl')}")


if __name__ == "__main__":
    main()
