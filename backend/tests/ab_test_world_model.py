"""
A/B 对比测试：世界模型反馈闭环 vs 无反馈

直观展示世界模型在三个场景下的效果差异：
  场景1：常规舆论演化（50轮 baseline）
  场景2：突发危机（第15轮注入高恐慌事件，看两组如何收敛/发散）
  场景3：官方干预（危机后第25轮注入官方声明，看信任恢复速度）

每个场景输出：
  - ASCII 折线图：panic / trust / polarization 轨迹对比
  - 关键指标数值对比表
  - 综合评分
"""

import os
import sys
import json
import math
import random
import shutil
import logging
import warnings
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import Counter

# 静默所有日志和 warnings（必须在导入业务模块之前设置）
logging.disable(logging.INFO)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from app.services.world_state import WorldStateEngine, WorldStateSnapshot, WorldEvent
from run_parallel_simulation import build_world_state_prompt


# ============== 显示工具 ==============

# ANSI 颜色（支持 Windows Terminal / PowerShell 7+）
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    PURPLE = "\033[95m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def ascii_chart(
    series_a: List[float],
    series_b: List[float],
    title: str,
    height: int = 12,
    width: int = 60,
    label_a: str = "A(no WM)",
    label_b: str = "B(WM)",
    lower_better: bool = False,
    event_rounds: List[int] = None,
):
    """绘制双序列 ASCII 折线图"""
    all_vals = series_a + series_b
    y_min = max(0.0, min(all_vals) - 0.05)
    y_max = min(1.0, max(all_vals) + 0.05)
    y_range = y_max - y_min if y_max > y_min else 0.01

    n = len(series_a)
    # 横轴采样
    step = max(1, n // width)
    sampled_a = [series_a[i] for i in range(0, n, step)]
    sampled_b = [series_b[i] for i in range(0, n, step)]
    sampled_rounds = [i for i in range(0, n, step)]
    cols = len(sampled_a)

    canvas = [[' ' for _ in range(cols)] for _ in range(height)]

    def y_to_row(v):
        row = int((1.0 - (v - y_min) / y_range) * (height - 1))
        return max(0, min(height - 1, row))

    # 画 A 序列
    for c, v in enumerate(sampled_a):
        r = y_to_row(v)
        if canvas[r][c] == ' ':
            canvas[r][c] = 'A'

    # 画 B 序列
    for c, v in enumerate(sampled_b):
        r = y_to_row(v)
        if canvas[r][c] == 'A':
            canvas[r][c] = '*'  # 重叠
        else:
            canvas[r][c] = 'B'

    # 画事件标记
    if event_rounds:
        for er in event_rounds:
            ci = er // step if step > 0 else er
            if 0 <= ci < cols:
                canvas[0][ci] = '!'

    # 输出
    print(f"\n  {C.BOLD}{title}{C.RESET}")
    print(f"  {C.DIM}{'─' * (cols + 8)}{C.RESET}")

    for r in range(height):
        # Y 轴标签
        if r == 0:
            label = f"{y_max:.2f}"
        elif r == height - 1:
            label = f"{y_min:.2f}"
        elif r == height // 2:
            label = f"{(y_min + y_max) / 2:.2f}"
        else:
            label = "    "
        line = f"  {label:>5}|"
        for c in range(cols):
            ch = canvas[r][c]
            if ch == 'A':
                line += f"{C.RED}{ch}{C.RESET}"
            elif ch == 'B':
                line += f"{C.GREEN}{ch}{C.RESET}"
            elif ch == '*':
                line += f"{C.YELLOW}{ch}{C.RESET}"
            elif ch == '!':
                line += f"{C.PURPLE}!{C.RESET}"
            else:
                line += f"{C.DIM}.{C.RESET}"
        print(line)

    # X 轴
    x_axis = "       " + "".join(
        f"{sampled_rounds[c]:<1}" if c % max(1, cols // 5) == 0 else " "
        for c in range(cols)
    )
    print(f"  {'':>5}+{'─' * cols}")
    print(f"  {C.DIM}{x_axis}{C.RESET}")
    print(f"       {C.DIM}Round →{C.RESET}")

    # 图例
    final_a = series_a[-1]
    final_b = series_b[-1]
    better_is_b = (final_b < final_a) if lower_better else (final_b > final_a)
    marker_b = "▲" if better_is_b else "▼"
    marker_a = "▼" if better_is_b else "▲"

    print(f"  {C.RED}── {label_a}: final={final_a:.3f} {marker_a}{C.RESET}   "
          f"{C.GREEN}── {label_b}: final={final_b:.3f} {marker_b}{C.RESET}   "
          f"{C.YELLOW}* overlap{C.RESET}")


def bar_compare(label: str, val_a: float, val_b: float, lower_better: bool = False, width: int = 30):
    """水平对比条形图"""
    bar_a = int(val_a * width)
    bar_b = int(val_b * width)

    better_is_b = (val_b < val_a) if lower_better else (val_b > val_a)
    diff = val_b - val_a
    diff_pct = diff / max(val_a, 0.001) * 100

    tag_b = f"{C.GREEN}◀ BETTER{C.RESET}" if better_is_b else ""
    tag_a = f"{C.GREEN}◀ BETTER{C.RESET}" if (not better_is_b and abs(diff) > 0.005) else ""

    print(f"  {label:<18}")
    print(f"    A {C.RED}{'█' * bar_a}{'░' * (width - bar_a)}{C.RESET} {val_a:.3f} {tag_a}")
    print(f"    B {C.GREEN}{'█' * bar_b}{'░' * (width - bar_b)}{C.RESET} {val_b:.3f} {tag_b}")
    if abs(diff) > 0.005:
        direction = "↓" if diff < 0 else "↑"
        print(f"      {C.CYAN}Δ = {diff:+.3f} ({direction}{abs(diff_pct):.1f}%){C.RESET}")
    print()


# ============== 模拟 Agent ==============

@dataclass
class MockAgent:
    agent_id: int
    name: str
    entity_type: str
    sentiment_bias: float  # -1.0(极负面) ~ +1.0(极正面)
    activity_level: float  # 0~1, 每轮发帖概率


MOCK_AGENTS = [
    MockAgent(0, "武汉大学", "University", sentiment_bias=0.3, activity_level=0.6),
    MockAgent(1, "在校学生A", "Student", sentiment_bias=-0.6, activity_level=0.85),
    MockAgent(2, "在校学生B", "Student", sentiment_bias=-0.4, activity_level=0.8),
    MockAgent(3, "教授", "Professor", sentiment_bias=-0.1, activity_level=0.5),
    MockAgent(4, "校友（护校派）", "Alumni", sentiment_bias=0.2, activity_level=0.65),
    MockAgent(5, "校友（批评派）", "Alumni", sentiment_bias=-0.5, activity_level=0.7),
    MockAgent(6, "记者", "Journalist", sentiment_bias=-0.2, activity_level=0.75),
    MockAgent(7, "家长", "Parent", sentiment_bias=-0.3, activity_level=0.55),
    MockAgent(8, "教育部门", "GovernmentAgency", sentiment_bias=0.1, activity_level=0.3),
    MockAgent(9, "自媒体", "MediaOutlet", sentiment_bias=-0.3, activity_level=0.9),
    MockAgent(10, "律师", "Lawyer", sentiment_bias=-0.1, activity_level=0.5),
    MockAgent(11, "普通网民A", "Person", sentiment_bias=-0.4, activity_level=0.7),
    MockAgent(12, "普通网民B", "Person", sentiment_bias=-0.2, activity_level=0.6),
    MockAgent(13, "普通网民C", "Person", sentiment_bias=0.1, activity_level=0.5),
    MockAgent(14, "KOL", "Celebrity", sentiment_bias=-0.3, activity_level=0.8),
]


NEGATIVE_PHRASES = [
    "太离谱了", "坚决反对", "强烈不满", "形式主义", "官僚主义",
    "程序不公", "缺乏透明", "不可接受", "失望至极", "虚假回应",
    "愤怒", "恐慌", "危机", "混乱", "崩溃", "维权",
]

POSITIVE_PHRASES = [
    "有错必纠值得肯定", "这是进步", "支持改革", "期待改善",
    "官方回应", "措施到位", "声明", "通报", "澄清", "落实",
]

NEUTRAL_PHRASES = [
    "关注事态发展", "等待更多信息", "理性看待", "静观其变",
    "已转发", "mark一下", "了解了", "看看后续",
]


def generate_action(
    agent: MockAgent,
    round_num: int,
    world_state: WorldStateSnapshot = None,
    use_world_model: bool = False,
) -> Dict:
    """
    模拟 Agent 产生一个动作

    A组：sentiment_bias 直接决定内容倾向
    B组：世界状态调制 sentiment_bias
    """
    effective_bias = agent.sentiment_bias

    if use_world_model and world_state:
        deviation = (
            abs(world_state.attention_level - 0.1) +
            abs(world_state.panic_level - 0.1) +
            abs(world_state.trust_level - 0.6) +
            abs(world_state.polarization_level - 0.1)
        ) / 4.0

        if deviation >= 0.15:
            stability_damper = 1.0 - world_state.stability_level * 0.6

            if agent.entity_type in ("University", "GovernmentAgency"):
                effective_bias += world_state.panic_level * 0.35 * stability_damper
                effective_bias += world_state.trust_level * 0.15
            elif agent.entity_type in ("Student", "Person"):
                effective_bias -= world_state.panic_level * 0.06 * stability_damper
                effective_bias += world_state.trust_level * 0.3
            elif agent.entity_type in ("Journalist", "MediaOutlet"):
                effective_bias -= world_state.attention_level * 0.05 * stability_damper
                effective_bias += world_state.trust_level * 0.15
            elif agent.entity_type in ("Alumni",):
                effective_bias += world_state.trust_level * 0.2
            else:
                effective_bias += world_state.trust_level * 0.15
                effective_bias -= world_state.panic_level * 0.03 * stability_damper

            if world_state.polarization_level > 0.4:
                polar_correction = (world_state.polarization_level - 0.4) * 0.15
                if effective_bias < 0:
                    effective_bias += polar_correction
                else:
                    effective_bias -= polar_correction * 0.5

    effective_bias = max(-1.0, min(1.0, effective_bias))

    r = random.random()
    neg_prob = max(0.1, 0.5 - effective_bias * 0.4)
    pos_prob = max(0.1, 0.5 + effective_bias * 0.4)
    total = neg_prob + pos_prob + 0.2
    neg_prob /= total
    pos_prob /= total

    if r < neg_prob:
        content = random.choice(NEGATIVE_PHRASES)
    elif r < neg_prob + pos_prob:
        content = random.choice(POSITIVE_PHRASES)
    else:
        content = random.choice(NEUTRAL_PHRASES)

    action_type = random.choice(["CREATE_POST", "COMMENT", "REPOST", "LIKE"])

    return {
        "action_type": action_type,
        "agent_id": agent.agent_id,
        "action_args": {"content": content} if action_type in ("CREATE_POST", "COMMENT") else {},
    }


def run_simulation(
    agents: List[MockAgent],
    total_rounds: int,
    use_world_model: bool,
    seed: int = 42,
    inject_events: Optional[Dict[int, List[Dict]]] = None,
) -> Tuple[WorldStateEngine, List[Dict]]:
    """
    运行一组模拟
    
    Args:
        inject_events: {round_num: [event_dict, ...]} 在指定轮次注入事件
    """
    random.seed(seed)
    tmp_dir = tempfile.mkdtemp(prefix=f"ab_{'B' if use_world_model else 'A'}_")

    engine = WorldStateEngine(sim_dir=tmp_dir, use_llm=False)
    history = []

    for round_num in range(total_rounds):
        # 注入事件（写入队列文件，update_state 会消费）
        if inject_events and round_num in inject_events:
            with open(engine.injected_events_path, 'w', encoding='utf-8') as f:
                json.dump(inject_events[round_num], f, ensure_ascii=False)

        actions = []
        for agent in agents:
            if random.random() < agent.activity_level:
                action = generate_action(
                    agent, round_num,
                    world_state=engine.current_state,
                    use_world_model=use_world_model,
                )
                actions.append(action)

        new_state, events = engine.update_state(round_num, actions)

        history.append({
            "round": round_num,
            "action_count": len(actions),
            "state": new_state.get_state_vector(),
            "events": [e.event_type for e in events],
        })

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return engine, history


def compute_behavior_entropy(history: List[Dict]) -> float:
    """计算行为多样性（状态轨迹的熵）"""
    buckets = Counter()
    for h in history:
        vec = h["state"]
        key = tuple(round(v * 5) / 5 for v in [vec["panic_level"], vec["trust_level"]])
        buckets[key] += 1

    total = sum(buckets.values())
    entropy = 0.0
    for count in buckets.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def extract_series(history: List[Dict], var: str) -> List[float]:
    return [h["state"][var] for h in history]


def compute_volatility(series: List[float]) -> float:
    """计算波动性（相邻轮次差异的标准差）"""
    if len(series) < 2:
        return 0.0
    diffs = [abs(series[i+1] - series[i]) for i in range(len(series) - 1)]
    mean_d = sum(diffs) / len(diffs)
    var_d = sum((d - mean_d) ** 2 for d in diffs) / len(diffs)
    return math.sqrt(var_d)


def compute_recovery_rounds(series: List[float], crisis_round: int, threshold: float = 0.4) -> int:
    """危机后恢复到 threshold 以下所需轮数（-1 表示未恢复）"""
    for i in range(crisis_round + 1, len(series)):
        if series[i] < threshold:
            return i - crisis_round
    return -1


def run_scenario(
    name: str,
    description: str,
    total_rounds: int,
    num_trials: int,
    inject_events: Optional[Dict[int, List[Dict]]] = None,
    event_rounds: List[int] = None,
):
    """运行一个完整的 A/B 场景"""
    print(f"\n{'=' * 72}")
    print(f"  {C.BOLD}{C.CYAN}SCENARIO: {name}{C.RESET}")
    print(f"  {C.DIM}{description}{C.RESET}")
    print(f"  {C.DIM}Rounds={total_rounds}  Trials={num_trials}  Agents={len(MOCK_AGENTS)}{C.RESET}")
    print(f"{'=' * 72}")

    all_a = {"panic": [], "trust": [], "polar": [], "stability": [], "entropy": [],
             "volatility": [], "events_count": []}
    all_b = {"panic": [], "trust": [], "polar": [], "stability": [], "entropy": [],
             "volatility": [], "events_count": []}

    last_hist_a = None
    last_hist_b = None

    for trial in range(num_trials):
        seed = 2000 + trial

        _, hist_a = run_simulation(MOCK_AGENTS, total_rounds, False, seed, inject_events)
        _, hist_b = run_simulation(MOCK_AGENTS, total_rounds, True, seed, inject_events)

        fa = hist_a[-1]["state"]
        fb = hist_b[-1]["state"]

        all_a["panic"].append(fa["panic_level"])
        all_a["trust"].append(fa["trust_level"])
        all_a["polar"].append(fa["polarization_level"])
        all_a["stability"].append(fa["stability_level"])
        all_a["entropy"].append(compute_behavior_entropy(hist_a))
        all_a["volatility"].append(compute_volatility(extract_series(hist_a, "panic_level")))
        all_a["events_count"].append(sum(len(h["events"]) for h in hist_a))

        all_b["panic"].append(fb["panic_level"])
        all_b["trust"].append(fb["trust_level"])
        all_b["polar"].append(fb["polarization_level"])
        all_b["stability"].append(fb["stability_level"])
        all_b["entropy"].append(compute_behavior_entropy(hist_b))
        all_b["volatility"].append(compute_volatility(extract_series(hist_b, "panic_level")))
        all_b["events_count"].append(sum(len(h["events"]) for h in hist_b))

        last_hist_a = hist_a
        last_hist_b = hist_b

    avg = lambda lst: sum(lst) / len(lst)

    # ---------- ASCII 折线图 ----------
    pa = extract_series(last_hist_a, "panic_level")
    pb = extract_series(last_hist_b, "panic_level")
    ta = extract_series(last_hist_a, "trust_level")
    tb = extract_series(last_hist_b, "trust_level")
    pola = extract_series(last_hist_a, "polarization_level")
    polb = extract_series(last_hist_b, "polarization_level")
    sa = extract_series(last_hist_a, "stability_level")
    sb = extract_series(last_hist_b, "stability_level")

    ascii_chart(pa, pb, f"Panic Level  (lower = better)", height=10,
                lower_better=True, event_rounds=event_rounds)
    ascii_chart(ta, tb, f"Trust Level  (higher = better)", height=10,
                event_rounds=event_rounds)
    ascii_chart(pola, polb, f"Polarization  (lower = better)", height=10,
                lower_better=True, event_rounds=event_rounds)

    # ---------- 指标对比条形图 ----------
    print(f"\n  {C.BOLD}Metric Comparison ({num_trials}-trial average){C.RESET}")
    print(f"  {'─' * 50}")

    bar_compare("Final Panic",     avg(all_a["panic"]),     avg(all_b["panic"]),     lower_better=True)
    bar_compare("Final Trust",     avg(all_a["trust"]),     avg(all_b["trust"]),     lower_better=False)
    bar_compare("Final Polar.",    avg(all_a["polar"]),     avg(all_b["polar"]),     lower_better=True)
    bar_compare("Final Stability", avg(all_a["stability"]), avg(all_b["stability"]), lower_better=False)
    bar_compare("Behavior Entropy",avg(all_a["entropy"]),   avg(all_b["entropy"]),   lower_better=False)
    bar_compare("Panic Volatility",avg(all_a["volatility"]),avg(all_b["volatility"]),lower_better=True)

    # ---------- 评分 ----------
    metrics = [
        ("Panic ↓",      "panic",      True),
        ("Trust ↑",      "trust",      False),
        ("Polar. ↓",     "polar",      True),
        ("Stability ↑",  "stability",  False),
        ("Entropy ↑",    "entropy",    False),
        ("Volatility ↓", "volatility", True),
    ]

    score_b = 0
    total_metrics = len(metrics)
    details = []

    for label, key, lower_better in metrics:
        va = avg(all_a[key])
        vb = avg(all_b[key])
        diff = vb - va
        win_b = (diff < -0.005) if lower_better else (diff > 0.005)
        if win_b:
            score_b += 1
            details.append(f"    {C.GREEN}✓ {label}: B wins ({diff:+.4f}){C.RESET}")
        elif abs(diff) < 0.005:
            score_b += 0.5
            details.append(f"    {C.YELLOW}─ {label}: tie ({diff:+.4f}){C.RESET}")
        else:
            details.append(f"    {C.RED}✗ {label}: A wins ({diff:+.4f}){C.RESET}")

    # 恢复速度（仅危机场景）
    if event_rounds and len(event_rounds) > 0:
        cr = event_rounds[0]
        rec_a = compute_recovery_rounds(pa, cr)
        rec_b = compute_recovery_rounds(pb, cr)
        total_metrics += 1
        if rec_b >= 0 and (rec_a < 0 or rec_b < rec_a):
            score_b += 1
            details.append(f"    {C.GREEN}✓ Recovery: B={rec_b}r vs A={'∞' if rec_a < 0 else rec_a}r{C.RESET}")
        elif rec_a >= 0 and (rec_b < 0 or rec_a < rec_b):
            details.append(f"    {C.RED}✗ Recovery: A={rec_a}r vs B={'∞' if rec_b < 0 else rec_b}r{C.RESET}")
        else:
            score_b += 0.5
            details.append(f"    {C.YELLOW}─ Recovery: both {'∞' if rec_a < 0 else rec_a}r{C.RESET}")

    print(f"\n  {C.BOLD}Scorecard{C.RESET}")
    print(f"  {'─' * 50}")
    for d in details:
        print(d)
    pct = score_b / total_metrics * 100
    color = C.GREEN if pct >= 60 else (C.YELLOW if pct >= 40 else C.RED)
    print(f"\n  {C.BOLD}World Model Win Rate: {color}{pct:.0f}% ({score_b}/{total_metrics}){C.RESET}")

    if pct >= 60:
        print(f"  {C.GREEN}{C.BOLD}→ VERDICT: World Model IMPROVES simulation quality{C.RESET}")
    elif pct >= 40:
        print(f"  {C.YELLOW}{C.BOLD}→ VERDICT: World Model has MARGINAL effect{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}→ VERDICT: World Model DEGRADES simulation, needs tuning{C.RESET}")

    return score_b, total_metrics


def main():
    # 启用 Windows 终端 ANSI 颜色支持
    if sys.platform == 'win32':
        os.system('')  # 激活 ANSI 转义序列

    print(f"\n{C.BOLD}{C.PURPLE}{'═' * 72}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  NexusMind World Model A/B Test Suite{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  A = No World Model (agents blind to environment){C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  B = With World Model (agents perceive & react to state){C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}{'═' * 72}{C.RESET}")

    total_score = 0
    total_possible = 0

    # ═══════ 场景 1：常规舆论演化 ═══════
    s1_score, s1_total = run_scenario(
        name="Baseline Evolution",
        description="Normal 50-round simulation, no external events.\n"
                    "  Tests whether WM feedback creates more realistic dynamics.",
        total_rounds=50,
        num_trials=5,
    )
    total_score += s1_score
    total_possible += s1_total

    # ═══════ 场景 2：突发危机 ═══════
    crisis_event = [{
        "event_type": "breaking_news",
        "description": "重大负面事件爆发：核心利益相关方发布严厉指控，引发全网关注",
        "severity": 0.9,
        "affected_variables": {
            "panic_level": 0.35,
            "trust_level": -0.25,
            "attention_level": 0.3,
        },
        "source": "god_mode",
    }]
    s2_score, s2_total = run_scenario(
        name="Crisis Injection (Panic Shock at R15)",
        description="Inject a severe crisis at round 15 (panic +0.35, trust -0.25).\n"
                    "  Tests WM's ability to propagate crisis impact and self-correct.",
        total_rounds=50,
        num_trials=5,
        inject_events={15: crisis_event},
        event_rounds=[15],
    )
    total_score += s2_score
    total_possible += s2_total

    # ═══════ 场景 3：危机 + 官方干预 ═══════
    official_response = [{
        "event_type": "official_statement",
        "description": "权威部门发布详细调查报告，承诺整改，公布具体时间表",
        "severity": 0.7,
        "affected_variables": {
            "trust_level": 0.30,
            "panic_level": -0.15,
            "stability_level": 0.10,
        },
        "source": "god_mode",
    }]
    s3_score, s3_total = run_scenario(
        name="Crisis + Official Intervention (R15 crisis, R25 response)",
        description="Crisis at R15, official response at R25.\n"
                    "  Tests WM's ability to model trust recovery after intervention.",
        total_rounds=60,
        num_trials=5,
        inject_events={15: crisis_event, 25: official_response},
        event_rounds=[15, 25],
    )
    total_score += s3_score
    total_possible += s3_total

    # ═══════ 总结 ═══════
    print(f"\n{'═' * 72}")
    print(f"  {C.BOLD}{C.CYAN}OVERALL SUMMARY{C.RESET}")
    print(f"{'═' * 72}")

    overall_pct = total_score / total_possible * 100

    print(f"\n  Scenarios tested: 3")
    print(f"  Total metrics:    {total_possible}")
    print(f"  WM wins:          {total_score}/{total_possible}")

    bar_len = 40
    filled = int(overall_pct / 100 * bar_len)
    color = C.GREEN if overall_pct >= 60 else (C.YELLOW if overall_pct >= 40 else C.RED)
    bar = f"{color}{'█' * filled}{'░' * (bar_len - filled)}{C.RESET}"
    print(f"\n  Overall Win Rate: {bar} {color}{C.BOLD}{overall_pct:.0f}%{C.RESET}")

    print()
    if overall_pct >= 65:
        print(f"  {C.GREEN}{C.BOLD}╔══════════════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.GREEN}{C.BOLD}║  CONCLUSION: World Model significantly improves  ║{C.RESET}")
        print(f"  {C.GREEN}{C.BOLD}║  simulation realism and crisis resilience.        ║{C.RESET}")
        print(f"  {C.GREEN}{C.BOLD}╚══════════════════════════════════════════════════╝{C.RESET}")
    elif overall_pct >= 45:
        print(f"  {C.YELLOW}{C.BOLD}╔══════════════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.YELLOW}{C.BOLD}║  CONCLUSION: World Model shows moderate benefit. ║{C.RESET}")
        print(f"  {C.YELLOW}{C.BOLD}║  Consider tuning feedback coefficients.           ║{C.RESET}")
        print(f"  {C.YELLOW}{C.BOLD}╚══════════════════════════════════════════════════╝{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}╔══════════════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.RED}{C.BOLD}║  CONCLUSION: World Model needs parameter tuning. ║{C.RESET}")
        print(f"  {C.RED}{C.BOLD}╚══════════════════════════════════════════════════╝{C.RESET}")

    print()


if __name__ == "__main__":
    main()
    sys.exit(0)
