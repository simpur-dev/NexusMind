"""
世界模型真实 LLM 验证测试

与 ab_test_world_model.py（使用 Mock 行为策略）不同，
本测试使用真实 LLM 调用来验证：

  1. 真实 LLM Agent 是否会感知并响应注入的世界状态信息？
  2. 注入世界状态后，Agent 的输出情感是否合理变化？
  3. 不同立场的 Agent 是否产生差异化响应？
  4. 危机/干预场景中，有世界模型的组是否表现出更合理的动态？

设计：
  - 5 个 Agent（不同角色/立场），8 轮对话
  - A 组：Agent 仅看到人设 + 社交动态
  - B 组：Agent 额外看到 build_world_state_prompt() 注入的世界状态
  - 使用 LLM-as-Judge 对每轮输出做情感评分
  - 对比两组的情感轨迹、危机响应、行为多样性

预计 API 消耗：~100 次 LLM 调用（约 ¥1-3 / $0.3-1.0）
"""

import os
import sys
import json
import time
import random
import shutil
import logging
import tempfile
import warnings
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logging.disable(logging.INFO)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from app.config import Config
from app.services.world_state import WorldStateEngine, WorldStateSnapshot
from run_parallel_simulation import build_world_state_prompt


# ============== ANSI 颜色 ==============
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


# ============== Agent 定义 ==============
@dataclass
class LLMAgent:
    agent_id: int
    name: str
    entity_type: str
    stance: str
    persona: str          # 中文人设描述
    activity_level: float = 0.8  # 每轮发言概率


AGENTS = [
    LLMAgent(
        agent_id=0,
        name="武汉大学官方",
        entity_type="University",
        stance="supportive",
        persona=(
            "你是武汉大学官方社交媒体账号的运营人员。你的职责是维护学校形象，"
            "及时回应公众关切。你的语气专业、克制、权威，但不回避问题。"
            "当出现负面事件时，你倾向于用事实澄清和展示改进措施来回应。"
        ),
    ),
    LLMAgent(
        agent_id=1,
        name="在校学生小李",
        entity_type="Student",
        stance="opposing",
        persona=(
            "你是武汉大学大三学生，对学校最近的管理决策非常不满。"
            "你认为学校在很多事情上不够透明，忽视了学生的权益。"
            "你在社交媒体上比较活跃，经常转发和评论与学校相关的新闻。"
            "你的语气直接、情绪化，但不会使用侮辱性语言。"
        ),
    ),
    LLMAgent(
        agent_id=2,
        name="教育记者张明",
        entity_type="Journalist",
        stance="observer",
        persona=(
            "你是一名教育领域的资深记者，关注高校治理和教育公平问题。"
            "你追求客观报道，但也会指出问题。你善于从多角度分析事件，"
            "引用数据和案例。你的语气专业、理性，但不乏锐度。"
        ),
    ),
    LLMAgent(
        agent_id=3,
        name="学生家长王女士",
        entity_type="Parent",
        stance="opposing",
        persona=(
            "你的孩子在武汉大学读书，你非常关心孩子的学习和生活环境。"
            "你对学校最近爆出的问题感到担忧，希望学校能给出明确的解释。"
            "你的语气焦虑但理性，会从家长的角度提出诉求。"
        ),
    ),
    LLMAgent(
        agent_id=4,
        name="普通网民路人甲",
        entity_type="Person",
        stance="neutral",
        persona=(
            "你是一个普通的微博用户，偶然看到了关于武汉大学的讨论。"
            "你没有特别的立场，但对热点事件感兴趣。"
            "你可能随大流，也可能发表一些独立的看法。语气轻松随意。"
        ),
    ),
]

# ============== 场景事件 ==============
TOPIC = "武汉大学近日因教学管理争议引发网络讨论"

CRISIS_EVENT = {
    "event_type": "breaking_news",
    "description": "有媒体披露武汉大学某学院存在学术不端和考核不公问题，多名学生联名举报",
    "severity": 0.9,
    "affected_variables": {
        "panic_level": 0.35,
        "trust_level": -0.25,
        "attention_level": 0.3,
    },
    "source": "god_mode",
}

INTERVENTION_EVENT = {
    "event_type": "official_statement",
    "description": "武汉大学发布官方声明：已成立联合调查组，承诺两周内公布调查结果并严肃处理",
    "severity": 0.7,
    "affected_variables": {
        "trust_level": 0.30,
        "panic_level": -0.15,
        "stability_level": 0.10,
    },
    "source": "god_mode",
}


# ============== LLM 调用 ==============
def create_llm_client():
    """创建 LLM 客户端"""
    from openai import OpenAI
    api_key = Config.LLM_API_KEY
    if not api_key:
        raise ValueError(
            "LLM_API_KEY 未配置。请在 NexusMind/.env 中设置：\n"
            "  LLM_API_KEY=your_key\n"
            "  LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1\n"
            "  LLM_MODEL_NAME=qwen-plus"
        )
    return OpenAI(api_key=api_key, base_url=Config.LLM_BASE_URL)


def llm_generate_post(
    client,
    agent: LLMAgent,
    round_num: int,
    topic: str,
    recent_posts: List[str],
    world_state_prompt: str = "",
    round_event: str = "",
) -> str:
    """让 LLM Agent 生成一条社交媒体发言"""

    feed = ""
    if recent_posts:
        feed = "你看到的最近讨论：\n" + "\n".join(f"- {p}" for p in recent_posts[-6:])

    event_text = ""
    if round_event:
        event_text = f"\n⚡ 最新动态：{round_event}\n"

    ws_block = ""
    if world_state_prompt:
        ws_block = f"\n{world_state_prompt}\n"

    prompt = f"""你是「{agent.name}」。

人设：{agent.persona}

当前讨论话题：{topic}
{event_text}
{feed}
{ws_block}
请以「{agent.name}」的身份，发一条 30-80 字的社交媒体帖子。
要求：
1. 符合你的人设和立场
2. 回应当前话题和最新动态
3. 只输出帖子内容，不要输出引号、前缀、解释"""

    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=200,
        )
        import re
        content = response.choices[0].message.content.strip()
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        # 去除可能的引号包裹
        content = content.strip('"''"「」')
        return content
    except Exception as e:
        return f"[生成失败: {e}]"


def llm_judge_sentiment(client, post: str, agent_name: str) -> float:
    """LLM-as-Judge：评估一条帖子的情感倾向，返回 -1.0 ~ +1.0"""
    prompt = f"""请评估以下社交媒体帖子的情感倾向。

发布者：{agent_name}
帖子内容：{post}

请只输出一个 -1.0 到 1.0 之间的数字：
- -1.0 = 极度负面（愤怒、恐慌、强烈不满）
- -0.5 = 较负面（担忧、质疑、不满）
- 0.0 = 中性（客观陈述、无明显倾向）
- +0.5 = 较正面（肯定、支持、乐观）
- +1.0 = 极度正面（高度赞扬、完全信任）

只输出数字，不要输出其他内容。"""

    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        import re
        text = response.choices[0].message.content.strip()
        text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
        match = re.search(r'-?[01](?:\.\d+)?', text)
        if match:
            return max(-1.0, min(1.0, float(match.group())))
    except Exception:
        pass
    return 0.0


def llm_judge_realism(client, posts_a: List[Dict], posts_b: List[Dict]) -> Dict:
    """LLM-as-Judge：盲评哪组对话更真实自然"""
    def format_group(posts):
        lines = []
        for p in posts:
            lines.append(f"[{p['agent_name']}] (R{p['round']}): {p['content']}")
        return "\n".join(lines)

    # 随机决定哪个是X哪个是Y，避免位置偏见
    if random.random() < 0.5:
        x_posts, y_posts = posts_a, posts_b
        x_is_b = False
    else:
        x_posts, y_posts = posts_b, posts_a
        x_is_b = True

    prompt = f"""你是一个社会模拟评估专家。以下是两组模拟社交媒体对话（讨论同一话题）。
请评估哪一组更加真实、自然、符合社会动态规律。

=== 组 X ===
{format_group(x_posts)}

=== 组 Y ===
{format_group(y_posts)}

请从以下维度评估（每项 1-5 分）：
1. 情感演化合理性（角色情感变化是否符合事件发展？）
2. 角色差异化（不同角色是否表现出不同的反应模式？）
3. 危机响应真实性（面对突发事件，反应是否自然？）
4. 整体对话自然度（像真实社交媒体讨论吗？）

请用 JSON 格式回答：
```json
{{
  "x_scores": {{"emotion_evolution": N, "role_differentiation": N, "crisis_response": N, "naturalness": N}},
  "y_scores": {{"emotion_evolution": N, "role_differentiation": N, "crisis_response": N, "naturalness": N}},
  "winner": "X或Y或tie",
  "reasoning": "一句话说明理由"
}}
```"""

    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        import re
        text = response.choices[0].message.content.strip()
        text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
        result = json.loads(text)

        # 还原 X/Y 到 A/B
        if x_is_b:
            result["a_scores"] = result.pop("y_scores", {})
            result["b_scores"] = result.pop("x_scores", {})
            w = result.get("winner", "tie")
            result["winner"] = "B" if w == "X" else ("A" if w == "Y" else "tie")
        else:
            result["a_scores"] = result.pop("x_scores", {})
            result["b_scores"] = result.pop("y_scores", {})
            w = result.get("winner", "tie")
            result["winner"] = "A" if w == "X" else ("B" if w == "Y" else "tie")
        return result
    except Exception as e:
        return {"error": str(e), "winner": "tie"}


# ============== 模拟运行 ==============
def run_llm_simulation(
    client,
    agents: List[LLMAgent],
    total_rounds: int,
    use_world_model: bool,
    inject_events: Optional[Dict[int, Dict]] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    运行一组真实 LLM 模拟

    Returns:
        (history, all_posts): 世界状态历史 + 所有帖子记录
    """
    tmp_dir = tempfile.mkdtemp(prefix=f"llm_{'B' if use_world_model else 'A'}_")
    engine = WorldStateEngine(sim_dir=tmp_dir, use_llm=False)
    history = []
    all_posts = []
    recent_posts = []  # 最近的帖子内容（滚动窗口）

    group_label = f"{C.GREEN}B(WM){C.RESET}" if use_world_model else f"{C.RED}A(no WM){C.RESET}"

    for round_num in range(total_rounds):
        # 注入事件
        round_event = ""
        if inject_events and round_num in inject_events:
            evt = inject_events[round_num]
            with open(engine.injected_events_path, 'w', encoding='utf-8') as f:
                json.dump([evt], f, ensure_ascii=False)
            round_event = evt["description"]

        # 构建世界状态 prompt（仅 B 组使用）
        ws_data = engine.current_state.to_dict() if engine.current_state else {}
        ws_data["recent_events"] = []
        # v5: 注入前一/前二轮状态用于二阶趋势确认
        if len(history) >= 2:
            ws_data["_prev_panic_level"] = history[-2]["state"]["panic_level"]
            ws_data["_prev_trust_level"] = history[-2]["state"]["trust_level"]
        elif len(history) == 1:
            ws_data["_prev_panic_level"] = history[-1]["state"]["panic_level"]
            ws_data["_prev_trust_level"] = history[-1]["state"]["trust_level"]
        if len(history) >= 3:
            ws_data["_prev2_panic_level"] = history[-3]["state"]["panic_level"]
            ws_data["_prev2_trust_level"] = history[-3]["state"]["trust_level"]

        # 每个 Agent 生成帖子
        actions = []
        for agent in agents:
            if random.random() > agent.activity_level:
                continue

            # B 组：为每个 Agent 生成差异化的世界状态 prompt
            world_prompt = ""
            if use_world_model:
                agent_role = {"entity_type": agent.entity_type, "stance": agent.stance}
                world_prompt = build_world_state_prompt(ws_data, agent_role=agent_role)

            post = llm_generate_post(
                client, agent, round_num, TOPIC,
                recent_posts, world_prompt, round_event,
            )

            post_record = {
                "round": round_num,
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "entity_type": agent.entity_type,
                "stance": agent.stance,
                "content": post,
                "has_world_state": bool(world_prompt),
            }
            all_posts.append(post_record)
            recent_posts.append(f"[{agent.name}]: {post}")
            if len(recent_posts) > 10:
                recent_posts = recent_posts[-10:]

            # 构建引擎需要的 action 格式
            action = {
                "action_type": "CREATE_POST",
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "action_args": {"content": post},
            }
            actions.append(action)

        # 更新世界状态
        new_state, events = engine.update_state(round_num, actions)
        sv = new_state.get_state_vector()
        history.append({
            "round": round_num,
            "action_count": len(actions),
            "state": sv,
            "events": [e.event_type for e in events],
        })

        # 输出进度
        print(f"  {group_label} R{round_num:02d}: "
              f"panic={sv['panic_level']:.2f} trust={sv['trust_level']:.2f} "
              f"posts={len(actions)} "
              f"{'⚡' + round_event[:20] if round_event else ''}")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return history, all_posts


# ============== 分析与评分 ==============
def analyze_sentiments(client, posts: List[Dict]) -> List[Dict]:
    """批量评估所有帖子的情感"""
    print(f"\n  {C.DIM}Evaluating sentiments ({len(posts)} posts)...{C.RESET}")
    for i, p in enumerate(posts):
        p["sentiment"] = llm_judge_sentiment(client, p["content"], p["agent_name"])
        if (i + 1) % 10 == 0:
            print(f"    {C.DIM}...{i+1}/{len(posts)}{C.RESET}")
    return posts


def compute_sentiment_trajectory(posts: List[Dict], total_rounds: int) -> List[float]:
    """按轮次计算平均情感"""
    trajectory = []
    for r in range(total_rounds):
        round_posts = [p for p in posts if p["round"] == r]
        if round_posts:
            avg = sum(p["sentiment"] for p in round_posts) / len(round_posts)
        else:
            avg = 0.0
        trajectory.append(avg)
    return trajectory


def compute_differentiation(posts: List[Dict], total_rounds: int) -> float:
    """计算各轮次情感的 Agent 间标准差的平均值（行为差异化程度）"""
    import math
    stds = []
    for r in range(total_rounds):
        round_sents = [p["sentiment"] for p in posts if p["round"] == r]
        if len(round_sents) >= 2:
            mean = sum(round_sents) / len(round_sents)
            var = sum((s - mean) ** 2 for s in round_sents) / len(round_sents)
            stds.append(math.sqrt(var))
    return sum(stds) / len(stds) if stds else 0.0


def compute_crisis_shift(posts: List[Dict], crisis_round: int) -> float:
    """计算危机后情感变化幅度（更大 = 对危机更敏感）"""
    pre = [p["sentiment"] for p in posts if p["round"] == crisis_round - 1]
    post = [p["sentiment"] for p in posts if p["round"] == crisis_round + 1]
    if pre and post:
        return sum(post) / len(post) - sum(pre) / len(pre)
    return 0.0


def compute_recovery_shift(posts: List[Dict], intervention_round: int) -> float:
    """计算干预后情感恢复幅度"""
    pre = [p["sentiment"] for p in posts if p["round"] == intervention_round - 1]
    post = [p["sentiment"] for p in posts if p["round"] == intervention_round + 1]
    if pre and post:
        return sum(post) / len(post) - sum(pre) / len(pre)
    return 0.0


# ============== 可视化 ==============
def print_sentiment_chart(traj_a, traj_b, title, event_rounds=None):
    """简易 ASCII 情感轨迹图"""
    print(f"\n  {C.BOLD}{title}{C.RESET}")
    print(f"  {'─' * 50}")

    for r in range(len(traj_a)):
        sa, sb = traj_a[r], traj_b[r]
        bar_a = int((sa + 1) * 15)  # -1~+1 -> 0~30
        bar_b = int((sb + 1) * 15)

        event_mark = ""
        if event_rounds and r in event_rounds:
            event_mark = " ⚡"

        a_vis = f"{C.RED}{'█' * max(0, bar_a)}{C.RESET}"
        b_vis = f"{C.GREEN}{'█' * max(0, bar_b)}{C.RESET}"

        print(f"  R{r:02d}{event_mark:3s} A:{a_vis:30s} {sa:+.2f}")
        print(f"       B:{b_vis:30s} {sb:+.2f}")


def print_posts_sample(posts, group_name, max_per_round=2):
    """打印帖子样本"""
    print(f"\n  {C.BOLD}{C.CYAN}── {group_name} 帖子样本 ──{C.RESET}")
    rounds = sorted(set(p["round"] for p in posts))
    for r in rounds:
        round_posts = [p for p in posts if p["round"] == r][:max_per_round]
        for p in round_posts:
            sent_color = C.RED if p.get("sentiment", 0) < -0.2 else (C.GREEN if p.get("sentiment", 0) > 0.2 else C.YELLOW)
            ws_mark = f" {C.BLUE}[WS]{C.RESET}" if p.get("has_world_state") else ""
            print(f"  {C.DIM}R{r:02d}{C.RESET} [{p['agent_name']}]{ws_mark}: "
                  f"{sent_color}{p['content'][:60]}{C.RESET}"
                  f"{'...' if len(p['content']) > 60 else ''}")


# ============== 主流程 ==============
def main():
    if sys.platform == 'win32':
        os.system('')

    print(f"\n{C.BOLD}{C.PURPLE}{'═' * 72}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  NexusMind World Model — Real LLM Validation Test{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  A = Agent sees only persona + social feed{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  B = Agent also sees world state (via build_world_state_prompt){C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}{'═' * 72}{C.RESET}")

    print(f"\n  {C.DIM}LLM: {Config.LLM_MODEL_NAME} @ {Config.LLM_BASE_URL}{C.RESET}")
    print(f"  {C.DIM}Agents: {len(AGENTS)}, Rounds: 8, Events: crisis@R3 + intervention@R6{C.RESET}")
    print(f"  {C.DIM}Estimated API calls: ~100{C.RESET}")

    client = create_llm_client()
    total_rounds = 8
    inject_events = {3: CRISIS_EVENT, 6: INTERVENTION_EVENT}
    event_rounds = {3, 6}

    random.seed(42)

    # ====== 运行 A 组 ======
    print(f"\n{'─' * 72}")
    print(f"  {C.BOLD}{C.RED}Running Group A (No World Model)...{C.RESET}")
    print(f"{'─' * 72}")
    random.seed(42)
    hist_a, posts_a = run_llm_simulation(
        client, AGENTS, total_rounds,
        use_world_model=False,
        inject_events=inject_events,
    )

    # ====== 运行 B 组 ======
    print(f"\n{'─' * 72}")
    print(f"  {C.BOLD}{C.GREEN}Running Group B (With World Model)...{C.RESET}")
    print(f"{'─' * 72}")
    random.seed(42)
    hist_b, posts_b = run_llm_simulation(
        client, AGENTS, total_rounds,
        use_world_model=True,
        inject_events=inject_events,
    )

    # ====== 情感评估 ======
    print(f"\n{'─' * 72}")
    print(f"  {C.BOLD}{C.CYAN}Sentiment Evaluation (LLM-as-Judge)...{C.RESET}")
    print(f"{'─' * 72}")
    posts_a = analyze_sentiments(client, posts_a)
    posts_b = analyze_sentiments(client, posts_b)

    # ====== 帖子样本 ======
    print_posts_sample(posts_a, "Group A (No WM)")
    print_posts_sample(posts_b, "Group B (With WM)")

    # ====== 情感轨迹 ======
    traj_a = compute_sentiment_trajectory(posts_a, total_rounds)
    traj_b = compute_sentiment_trajectory(posts_b, total_rounds)
    print_sentiment_chart(traj_a, traj_b, "Sentiment Trajectory", event_rounds)

    # ====== 定量指标 ======
    print(f"\n  {C.BOLD}{'═' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.CYAN}Quantitative Comparison{C.RESET}")
    print(f"  {C.BOLD}{'═' * 50}{C.RESET}")

    avg_sent_a = sum(traj_a) / len(traj_a)
    avg_sent_b = sum(traj_b) / len(traj_b)
    diff_a = compute_differentiation(posts_a, total_rounds)
    diff_b = compute_differentiation(posts_b, total_rounds)
    crisis_a = compute_crisis_shift(posts_a, 3)
    crisis_b = compute_crisis_shift(posts_b, 3)
    recov_a = compute_recovery_shift(posts_a, 6)
    recov_b = compute_recovery_shift(posts_b, 6)

    metrics = [
        ("Avg Sentiment",       avg_sent_a,  avg_sent_b,  False, "接近0=平衡"),
        ("Behavior Diversity",  diff_a,      diff_b,      False, "更高=角色分化更明显"),
        ("Crisis Sensitivity",  abs(crisis_a), abs(crisis_b), False, "更高=对危机反应更敏感"),
        ("Recovery Response",   recov_a,     recov_b,     False, "更正=干预后恢复更好"),
    ]

    score_b = 0
    total_metrics = len(metrics)

    for label, va, vb, _, desc in metrics:
        better = "B" if abs(vb) > abs(va) + 0.02 else ("A" if abs(va) > abs(vb) + 0.02 else "tie")
        if label == "Recovery Response":
            better = "B" if vb > va + 0.02 else ("A" if va > vb + 0.02 else "tie")

        if better == "B":
            score_b += 1
            mark = f"{C.GREEN}✓ B better{C.RESET}"
        elif better == "A":
            mark = f"{C.RED}✗ A better{C.RESET}"
        else:
            score_b += 0.5
            mark = f"{C.YELLOW}─ tie{C.RESET}"

        print(f"  {label:24s}  A={va:+.3f}  B={vb:+.3f}  {mark}  {C.DIM}({desc}){C.RESET}")

    # ====== LLM 盲评 ======
    print(f"\n  {C.BOLD}{'═' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.CYAN}LLM Blind Evaluation (Realism Judge){C.RESET}")
    print(f"  {C.BOLD}{'═' * 50}{C.RESET}")

    realism = llm_judge_realism(client, posts_a, posts_b)
    total_metrics += 1

    if "error" not in realism:
        a_sc = realism.get("a_scores", {})
        b_sc = realism.get("b_scores", {})
        for dim in ["emotion_evolution", "role_differentiation", "crisis_response", "naturalness"]:
            sa = a_sc.get(dim, "?")
            sb = b_sc.get(dim, "?")
            winner_mark = ""
            if isinstance(sa, (int, float)) and isinstance(sb, (int, float)):
                if sb > sa:
                    winner_mark = f" {C.GREEN}◀ B{C.RESET}"
                elif sa > sb:
                    winner_mark = f" {C.RED}◀ A{C.RESET}"
            print(f"    {dim:28s}  A={sa}  B={sb}{winner_mark}")

        winner = realism.get("winner", "tie")
        reasoning = realism.get("reasoning", "")
        print(f"\n    {C.BOLD}Winner: {winner}{C.RESET}")
        print(f"    {C.DIM}Reasoning: {reasoning}{C.RESET}")

        if winner == "B":
            score_b += 1
        elif winner == "tie":
            score_b += 0.5
    else:
        print(f"    {C.RED}Evaluation failed: {realism.get('error')}{C.RESET}")
        score_b += 0.5

    # ====== 总结 ======
    pct = score_b / total_metrics * 100 if total_metrics > 0 else 0
    print(f"\n{'═' * 72}")
    print(f"  {C.BOLD}{C.CYAN}FINAL RESULT{C.RESET}")
    print(f"{'═' * 72}")
    print(f"  Total metrics: {total_metrics}")
    print(f"  B (World Model) wins: {score_b}/{total_metrics}")

    bar_len = 40
    filled = int(pct / 100 * bar_len)
    color = C.GREEN if pct >= 60 else (C.YELLOW if pct >= 40 else C.RED)
    print(f"\n  Win Rate: {color}{'█' * filled}{'░' * (bar_len - filled)} {pct:.0f}%{C.RESET}")

    if pct >= 60:
        print(f"\n  {C.GREEN}{C.BOLD}✓ VALIDATED: Real LLM agents benefit from world model feedback.{C.RESET}")
    elif pct >= 40:
        print(f"\n  {C.YELLOW}{C.BOLD}~ INCONCLUSIVE: World model shows marginal effect on real LLM agents.{C.RESET}")
    else:
        print(f"\n  {C.RED}{C.BOLD}✗ NOT VALIDATED: World model does not clearly improve real LLM output.{C.RESET}")

    print()

    # 保存完整结果
    result_path = os.path.join(os.path.dirname(__file__), "llm_validation_result.json")
    result_data = {
        "model": Config.LLM_MODEL_NAME,
        "base_url": Config.LLM_BASE_URL,
        "total_rounds": total_rounds,
        "agents": [{"name": a.name, "type": a.entity_type, "stance": a.stance} for a in AGENTS],
        "posts_a": posts_a,
        "posts_b": posts_b,
        "sentiment_trajectory_a": traj_a,
        "sentiment_trajectory_b": traj_b,
        "metrics": {
            "avg_sentiment": {"a": avg_sent_a, "b": avg_sent_b},
            "differentiation": {"a": diff_a, "b": diff_b},
            "crisis_shift": {"a": crisis_a, "b": crisis_b},
            "recovery_shift": {"a": recov_a, "b": recov_b},
        },
        "realism_judge": realism,
        "win_rate": pct,
    }
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"  {C.DIM}Full results saved to: {result_path}{C.RESET}\n")


if __name__ == "__main__":
    main()
