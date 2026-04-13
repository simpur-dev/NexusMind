"""
A/B 对比测试：世界模型反馈闭环 vs 无反馈

设计思路：
  不调 LLM，而是用规则模拟 Agent 行为，验证世界模型闭环
  是否能在宏观指标上产生有意义的差异。

模拟规则（近似真实 LLM Agent 行为）：
  - Agent 基础发帖概率由 persona 的 sentiment_bias 决定
  - A组（无世界状态）：Agent 行为只受自身 persona 驱动
  - B组（有世界状态）：Agent 行为额外受世界状态影响
    - 恐慌高 → 负面发帖概率增加（正反馈）
    - 信任高 → 负面发帖概率降低（负反馈/阻尼）
    - 阻尼机制：偏离度 < 0.15 时世界状态不影响行为

对比指标：
  1. 最终恐慌水平
  2. 最终信任水平
  3. 最终极化程度
  4. 行为多样性（熵）
  5. 恐慌是否失控（> 0.95 判为失控）
"""

import os
import sys
import math
import random
import shutil
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from app.services.world_state import WorldStateEngine, WorldStateSnapshot
from run_parallel_simulation import build_world_state_prompt


# ============== 模拟 Agent ==============

@dataclass
class MockAgent:
    agent_id: int
    name: str
    entity_type: str
    sentiment_bias: float  # -1.0(极负面) ~ +1.0(极正面)
    activity_level: float  # 0~1, 每轮发帖概率


# 用真实配置中的 Agent 子集
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
    # 基础情感倾向
    effective_bias = agent.sentiment_bias

    if use_world_model and world_state:
        # 计算偏离度
        deviation = (
            abs(world_state.attention_level - 0.1) +
            abs(world_state.panic_level - 0.1) +
            abs(world_state.trust_level - 0.6) +
            abs(world_state.polarization_level - 0.1)
        ) / 4.0

        # 阻尼：偏离度 < 0.15 时不影响行为（与 build_world_state_prompt 一致）
        if deviation >= 0.15:
            # 稳定性衰减：环境越稳定，世界状态对行为的影响越弱
            stability_damper = 1.0 - world_state.stability_level * 0.6
            
            # 不同类型 Agent 对环境的反应不同（论文 §5.1.3 Social Influence）
            if agent.entity_type in ("University", "GovernmentAgency"):
                # 机构类：恐慌高 → 倾向发布安抚内容（强负反馈）
                effective_bias += world_state.panic_level * 0.35 * stability_damper
                effective_bias += world_state.trust_level * 0.15
            elif agent.entity_type in ("Student", "Person"):
                # 学生/普通人：恐慌高 → 轻微正反馈（系数小）
                effective_bias -= world_state.panic_level * 0.06 * stability_damper
                # 信任高 → 强负反馈（看到官方回应则显著安心）
                effective_bias += world_state.trust_level * 0.3
            elif agent.entity_type in ("Journalist", "MediaOutlet"):
                # 媒体：关注度高 → 更活跃但中性化
                effective_bias -= world_state.attention_level * 0.05 * stability_damper
                effective_bias += world_state.trust_level * 0.15
            elif agent.entity_type in ("Alumni",):
                # 校友：信任高 → 向中间靠拢
                effective_bias += world_state.trust_level * 0.2
            else:
                # 默认：信任有缓和效应
                effective_bias += world_state.trust_level * 0.15
                effective_bias -= world_state.panic_level * 0.03 * stability_damper
            
            # 极化负反馈（所有类型通用）：极化高时所有人向中间缓和
            # 现实中，舆论极化过度时平台介入/群体疏离感会产生缓和效应
            if world_state.polarization_level > 0.4:
                polar_correction = (world_state.polarization_level - 0.4) * 0.15
                if effective_bias < 0:
                    effective_bias += polar_correction  # 负面 agent 变缓和
                else:
                    effective_bias -= polar_correction * 0.5  # 正面 agent 也稍微收敛

    # 限制范围
    effective_bias = max(-1.0, min(1.0, effective_bias))

    # 根据 bias 随机选择内容类型
    r = random.random()
    neg_prob = max(0.1, 0.5 - effective_bias * 0.4)
    pos_prob = max(0.1, 0.5 + effective_bias * 0.4)
    # 归一化
    total = neg_prob + pos_prob + 0.2
    neg_prob /= total
    pos_prob /= total

    if r < neg_prob:
        content = random.choice(NEGATIVE_PHRASES)
    elif r < neg_prob + pos_prob:
        content = random.choice(POSITIVE_PHRASES)
    else:
        content = random.choice(NEUTRAL_PHRASES)

    # 决定动作类型
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
) -> Tuple[WorldStateEngine, List[Dict]]:
    """运行一组模拟"""
    random.seed(seed)
    tmp_dir = tempfile.mkdtemp(prefix=f"ab_{'B' if use_world_model else 'A'}_")

    engine = WorldStateEngine(sim_dir=tmp_dir, use_llm=False)
    history = []

    for round_num in range(total_rounds):
        # 每轮 Agent 按活跃度随机行动
        actions = []
        for agent in agents:
            if random.random() < agent.activity_level:
                action = generate_action(
                    agent, round_num,
                    world_state=engine.current_state,
                    use_world_model=use_world_model,
                )
                actions.append(action)

        # 更新世界状态
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
    # 把每轮状态离散化后计算分布
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


def main():
    TOTAL_ROUNDS = 50
    NUM_TRIALS = 5  # 多次试验取平均

    print("=" * 70)
    print("A/B 对比测试：世界模型反馈闭环效果验证")
    print("=" * 70)
    print(f"Agent 数量: {len(MOCK_AGENTS)}")
    print(f"模拟轮数: {TOTAL_ROUNDS}")
    print(f"重复试验: {NUM_TRIALS}")
    print(f"A组: 无世界模型反馈（Agent 行为纯 persona 驱动）")
    print(f"B组: 有世界模型反馈（Agent 感知环境状态，差异化响应）")
    print()

    results_a = {"panic": [], "trust": [], "polar": [], "stability": [], "entropy": [], "runaway": 0}
    results_b = {"panic": [], "trust": [], "polar": [], "stability": [], "entropy": [], "runaway": 0}

    for trial in range(NUM_TRIALS):
        seed = 1000 + trial

        # A组：无世界模型
        engine_a, history_a = run_simulation(MOCK_AGENTS, TOTAL_ROUNDS, use_world_model=False, seed=seed)
        final_a = engine_a.current_state
        results_a["panic"].append(final_a.panic_level)
        results_a["trust"].append(final_a.trust_level)
        results_a["polar"].append(final_a.polarization_level)
        results_a["stability"].append(final_a.stability_level)
        results_a["entropy"].append(compute_behavior_entropy(history_a))
        if final_a.panic_level > 0.95:
            results_a["runaway"] += 1

        # B组：有世界模型
        engine_b, history_b = run_simulation(MOCK_AGENTS, TOTAL_ROUNDS, use_world_model=True, seed=seed)
        final_b = engine_b.current_state
        results_b["panic"].append(final_b.panic_level)
        results_b["trust"].append(final_b.trust_level)
        results_b["polar"].append(final_b.polarization_level)
        results_b["stability"].append(final_b.stability_level)
        results_b["entropy"].append(compute_behavior_entropy(history_b))
        if final_b.panic_level > 0.95:
            results_b["runaway"] += 1

    # ============ 输出对比 ============
    def avg(lst):
        return sum(lst) / len(lst)

    print("=" * 70)
    print(f"{'指标':<20} {'A组(无世界模型)':<20} {'B组(有世界模型)':<20} {'差异':<15}")
    print("-" * 70)

    metrics = [
        ("最终恐慌水平", "panic", "lower_better"),
        ("最终信任水平", "trust", "higher_better"),
        ("最终极化程度", "polar", "lower_better"),
        ("最终稳定性", "stability", "higher_better"),
        ("行为多样性(熵)", "entropy", "higher_better"),
    ]

    score_a = 0
    score_b = 0

    for label, key, direction in metrics:
        va = avg(results_a[key])
        vb = avg(results_b[key])
        diff = vb - va
        if direction == "lower_better":
            winner = "B更优" if diff < -0.01 else ("A更优" if diff > 0.01 else "持平")
            if diff < -0.01:
                score_b += 1
            elif diff > 0.01:
                score_a += 1
        else:
            winner = "B更优" if diff > 0.01 else ("A更优" if diff < -0.01 else "持平")
            if diff > 0.01:
                score_b += 1
            elif diff < -0.01:
                score_a += 1

        print(f"{label:<20} {va:<20.4f} {vb:<20.4f} {diff:>+.4f} ({winner})")

    print(f"{'恐慌失控次数':<20} {results_a['runaway']}/{NUM_TRIALS:<17} {results_b['runaway']}/{NUM_TRIALS:<17}", end="")
    if results_b["runaway"] < results_a["runaway"]:
        print(" B更安全")
        score_b += 1
    elif results_b["runaway"] > results_a["runaway"]:
        print(" A更安全")
        score_a += 1
    else:
        print(" 持平")

    print("-" * 70)
    print(f"综合: A 胜 {score_a} 项, B 胜 {score_b} 项")
    print()

    if score_b > score_a:
        print("✅ 结论: 世界模型反馈闭环 【改善】 了模拟质量")
    elif score_a > score_b:
        print("⚠️  结论: 世界模型反馈闭环 【恶化】 了模拟质量，需要调参")
    else:
        print("➡️  结论: 两组效果相当，世界模型影响有限")

    # ============ 详细轨迹对比（最后一次试验） ============
    print()
    print("=" * 70)
    print("最后一次试验的状态轨迹对比（每10轮采样）")
    print("=" * 70)
    print(f"{'轮次':<6} {'A恐慌':<8} {'B恐慌':<8} {'A信任':<8} {'B信任':<8} {'A极化':<8} {'B极化':<8}")
    print("-" * 54)
    for i in range(0, TOTAL_ROUNDS, 10):
        sa = history_a[i]["state"]
        sb = history_b[i]["state"]
        print(
            f"{i:<6} "
            f"{sa['panic_level']:<8.3f} {sb['panic_level']:<8.3f} "
            f"{sa['trust_level']:<8.3f} {sb['trust_level']:<8.3f} "
            f"{sa['polarization_level']:<8.3f} {sb['polarization_level']:<8.3f}"
        )
    # 最终轮
    sa = history_a[-1]["state"]
    sb = history_b[-1]["state"]
    print(
        f"{TOTAL_ROUNDS-1:<6} "
        f"{sa['panic_level']:<8.3f} {sb['panic_level']:<8.3f} "
        f"{sa['trust_level']:<8.3f} {sb['trust_level']:<8.3f} "
        f"{sa['polarization_level']:<8.3f} {sb['polarization_level']:<8.3f}"
    )


if __name__ == "__main__":
    main()
