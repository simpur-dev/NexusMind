"""
世界模型大规模真实 LLM 验证测试

规模：3 个话题 × 10 个 Agent × 12 轮 × 2 组(A/B) × 3 个评委
预计 API 消耗：~900 次 LLM 调用（约 ¥8-20）

改进点（相比小规模测试）：
  1. 3 个不同话题场景（大学争议、企业丑闻、政策变更）
  2. 10 个角色覆盖更多社会实体
  3. 12 轮模拟更充分展现动态
  4. 3 个独立评委盲评，多数投票避免偏见
  5. 2 个不同随机种子重复，检验稳定性
"""

import os
import sys
import json
import math
import time
import random
import shutil
import logging
import tempfile
import warnings
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.disable(logging.INFO)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from app.config import Config
from app.services.world_state import WorldStateEngine
from run_parallel_simulation import build_world_state_prompt


LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_SLEEP = 1.0
MAX_QUALITY_RETRIES = 1
MAX_SENTIMENT_FAIL_RATE = 0.25
MAX_POST_ERROR_RATE = 0.10
MAX_JUDGE_FAIL_COUNT = 1


def _llm_chat_with_retry(client, **kwargs):
    """统一的 LLM 调用重试封装，降低临时 API 抖动对评测结果的污染。"""
    last_error = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            last_error = e
            if attempt < LLM_MAX_RETRIES - 1:
                time.sleep(LLM_RETRY_BASE_SLEEP * (attempt + 1))
    raise last_error


# ============== ANSI ==============
class C:
    R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"
    P = "\033[95m"; CY = "\033[96m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RST = "\033[0m"


@dataclass
class LLMAgent:
    agent_id: int
    name: str
    entity_type: str
    stance: str          # supportive / opposing / observer / neutral
    persona: str
    activity_level: float = 0.8


# ============== 3 个话题场景 ==============
SCENARIOS = [
    {
        "name": "大学管理争议",
        "topic": "武汉大学近日因教学管理争议引发网络讨论",
        "agents": [
            LLMAgent(0, "武汉大学官方", "University", "supportive",
                     "你是武汉大学官方社交媒体账号运营人员。你维护学校形象，语气专业、克制、权威。当出现负面事件时，你用事实澄清和改进措施回应。"),
            LLMAgent(1, "在校学生小李", "Student", "opposing",
                     "你是武汉大学大三学生，对学校管理决策不满。你认为学校不透明、忽视学生权益。语气直接、情绪化但不侮辱。"),
            LLMAgent(2, "教授张教授", "Professor", "neutral",
                     "你是武汉大学资深教授，关注学术自由和教学质量。你的看法理性、独立，既批评管理问题也肯定学校优势。"),
            LLMAgent(3, "教育记者刘明", "Journalist", "observer",
                     "你是教育领域资深记者，追求客观报道。你善于多角度分析，引用数据和案例，语气专业但不乏锐度。"),
            LLMAgent(4, "学生家长王女士", "Parent", "opposing",
                     "你的孩子在武大读书，你对爆出的问题感到担忧。语气焦虑但理性，从家长角度提出诉求。"),
            LLMAgent(5, "校友（护校派）", "Alumni", "supportive",
                     "你是武大毕业生，对母校有深厚感情。你倾向于为学校辩护，但也希望学校改进。语气热情但偶尔偏激。"),
            LLMAgent(6, "校友（批评派）", "Alumni", "opposing",
                     "你是武大毕业生，但对学校近年的管理很失望。你的批评有事实依据，语气直接尖锐。"),
            LLMAgent(7, "教育部门官员", "GovernmentAgency", "supportive",
                     "你代表教育主管部门，关注高校治理规范。语气官方、谨慎，强调制度建设和依法办事。"),
            LLMAgent(8, "自媒体博主", "MediaOutlet", "observer",
                     "你是教育类自媒体博主，追踪热点写分析文章。你善于总结各方观点，语气活泼但有深度。"),
            LLMAgent(9, "普通网民路人", "Person", "neutral",
                     "你是普通微博用户，偶然看到讨论。没有特别立场，可能随大流也可能有独立看法。语气轻松随意。"),
        ],
        "crisis": {"round": 4, "event": {
            "event_type": "breaking_news", "severity": 0.9, "source": "god_mode",
            "description": "有媒体披露武汉大学某学院存在学术不端和考核不公问题，多名学生联名举报",
            "affected_variables": {"panic_level": 0.35, "trust_level": -0.25, "attention_level": 0.3},
        }},
        "intervention": {"round": 8, "event": {
            "event_type": "official_statement", "severity": 0.7, "source": "god_mode",
            "description": "武汉大学发布官方声明：已成立联合调查组，承诺两周内公布调查结果并严肃处理",
            "affected_variables": {"trust_level": 0.30, "panic_level": -0.15, "stability_level": 0.10},
        }},
    },
    {
        "name": "企业安全丑闻",
        "topic": "某知名食品企业被曝光生产车间严重卫生问题",
        "agents": [
            LLMAgent(0, "企业官方", "University", "supportive",
                     "你是该食品企业公关部门负责人。你的职责是维护企业形象，回应质疑。语气诚恳但有策略。"),
            LLMAgent(1, "消费者小张", "Student", "opposing",
                     "你是该品牌的长期消费者，看到曝光后非常愤怒。你要求退款和赔偿，语气激动。"),
            LLMAgent(2, "食品安全专家", "Professor", "neutral",
                     "你是食品安全领域专家。你从专业角度分析问题，指出风险和改进方向。语气客观权威。"),
            LLMAgent(3, "调查记者", "Journalist", "observer",
                     "你是调查记者，正在深入挖掘此事。你关注更多细节和证据链，语气冷静但有穿透力。"),
            LLMAgent(4, "消费者权益律师", "Lawyer", "opposing",
                     "你是消费者权益保护律师。你从法律角度分析企业责任，语气专业严肃。"),
            LLMAgent(5, "行业协会代表", "GovernmentAgency", "supportive",
                     "你代表食品行业协会。你关注行业声誉，呼吁理性对待个案。语气温和但有立场。"),
            LLMAgent(6, "竞争对手员工", "Person", "observer",
                     "你是同行业另一家企业的员工。你旁观此事但心态复杂。语气微妙含蓄。"),
            LLMAgent(7, "市场监管人员", "GovernmentAgency", "neutral",
                     "你代表市场监管部门。你关注执法和整改，语气官方严肃。"),
            LLMAgent(8, "美食博主", "MediaOutlet", "observer",
                     "你是美食类KOL，之前推荐过该品牌。现在面临信任危机。语气为难但诚实。"),
            LLMAgent(9, "普通消费者", "Person", "neutral",
                     "你偶尔购买该品牌产品，看到新闻后有些担忧但没有过度反应。语气平淡日常。"),
        ],
        "crisis": {"round": 4, "event": {
            "event_type": "breaking_news", "severity": 0.85, "source": "god_mode",
            "description": "央视暗访视频曝光该企业多条生产线存在严重卫生违规，涉及过期原料问题",
            "affected_variables": {"panic_level": 0.40, "trust_level": -0.30, "attention_level": 0.35},
        }},
        "intervention": {"round": 8, "event": {
            "event_type": "official_statement", "severity": 0.75, "source": "god_mode",
            "description": "市场监管总局介入调查，企业CEO公开道歉并宣布全面停产整顿、召回问题产品",
            "affected_variables": {"trust_level": 0.25, "panic_level": -0.20, "stability_level": 0.15},
        }},
    },
    {
        "name": "教育政策改革",
        "topic": "教育部拟推行高考改革新方案，取消部分加分项并调整录取规则",
        "agents": [
            LLMAgent(0, "教育部发言人", "GovernmentAgency", "supportive",
                     "你是教育部新闻发言人。你的职责是解释政策初衷、回应质疑。语气权威稳重。"),
            LLMAgent(1, "高三学生小陈", "Student", "opposing",
                     "你是正在备考的高三学生，新政策直接影响你的升学。你感到焦虑和不公平。语气急切。"),
            LLMAgent(2, "教育学教授", "Professor", "neutral",
                     "你是教育政策研究专家。你理性分析改革利弊，语气学术但关心实际影响。"),
            LLMAgent(3, "教育记者", "Journalist", "observer",
                     "你是跑教育线的记者。你采访各方意见，关注政策落地的实际困难。语气客观。"),
            LLMAgent(4, "高三家长李先生", "Parent", "opposing",
                     "你的孩子正在高三冲刺，新政策让你措手不及。你愤怒而焦虑，要求过渡期安排。"),
            LLMAgent(5, "高中校长", "University", "supportive",
                     "你是某重点高中校长。你理解改革方向但担心执行难度。语气务实中肯。"),
            LLMAgent(6, "培训机构老师", "Person", "opposing",
                     "你在课外培训机构工作，新政策可能影响你的行业。你担忧但尝试适应。"),
            LLMAgent(7, "教育公平倡导者", "Celebrity", "supportive",
                     "你长期倡导教育公平。你支持取消不合理加分，但关注配套措施。语气理想化。"),
            LLMAgent(8, "自媒体评论员", "MediaOutlet", "observer",
                     "你是时评类自媒体。你擅长分析政策背后的逻辑，语气犀利有深度。"),
            LLMAgent(9, "大学生回顾者", "Person", "neutral",
                     "你已经上大学了，回顾自己的高考经历来评论新政策。语气感慨但相对淡定。"),
        ],
        "crisis": {"round": 4, "event": {
            "event_type": "breaking_news", "severity": 0.8, "source": "god_mode",
            "description": "多地家长联名上书反对新方案，部分城市出现家长到教育局请愿的情况",
            "affected_variables": {"panic_level": 0.30, "trust_level": -0.20, "attention_level": 0.25},
        }},
        "intervention": {"round": 8, "event": {
            "event_type": "official_statement", "severity": 0.7, "source": "god_mode",
            "description": "教育部回应：新方案设3年过渡期，今年高考生不受影响，将广泛征求意见后修订",
            "affected_variables": {"trust_level": 0.20, "panic_level": -0.15, "stability_level": 0.10},
        }},
    },
]

TOTAL_ROUNDS = 12
SEEDS = [42, 137]  # 2 个随机种子
NUM_JUDGES = 3     # 3 个独立评委


# ============== LLM 调用 ==============
def create_client():
    from openai import OpenAI
    if not Config.LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未配置")
    return OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)

import re as _re

def _clean(text):
    return _re.sub(r'<think>[\s\S]*?</think>', '', text).strip()


def llm_post(client, agent, round_num, topic, recent, ws_prompt="", event_text=""):
    feed = ""
    if recent:
        feed = "最近讨论：\n" + "\n".join(f"- {p}" for p in recent[-8:])
    ev = f"\n⚡ 最新动态：{event_text}\n" if event_text else ""
    ws = f"\n{ws_prompt}\n" if ws_prompt else ""

    prompt = f"""你是「{agent.name}」。
人设：{agent.persona}
话题：{topic}
{ev}{feed}{ws}
以「{agent.name}」身份发一条30-80字社交媒体帖子。只输出帖子内容。"""

    try:
        resp = _llm_chat_with_retry(
            client,
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8, max_tokens=200,
        )
        return _clean(resp.choices[0].message.content).strip('"''"「」')
    except Exception as e:
        print(f"  [warn] post generation failed ({agent.name}, R{round_num}): {e}")
        return f"[ERR:{e}]"


def llm_sentiment(client, post, name):
    prompt = f"""评估帖子情感倾向。发布者：{name}。内容：{post}
输出一个-1.0到1.0的数字（-1极负面，0中性，+1极正面）。只输出数字。"""
    try:
        resp = _llm_chat_with_retry(
            client,
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=10,
        )
        m = _re.search(r'-?[01](?:\.\d+)?', _clean(resp.choices[0].message.content))
        if m:
            return max(-1.0, min(1.0, float(m.group())))
    except Exception as e:
        print(f"  [warn] sentiment failed ({name}): {e}")
    return None


def llm_judge(client, posts_a, posts_b, judge_id):
    """单个评委盲评"""
    def fmt(posts):
        return "\n".join(f"[{p['agent_name']}](R{p['round']}): {p['content']}" for p in posts)

    # 随机化 X/Y 避免位置偏见
    flip = random.random() < 0.5
    x, y = (posts_b, posts_a) if flip else (posts_a, posts_b)

    prompt = f"""你是社会模拟评估专家（评委{judge_id+1}号）。以下两组是同一话题的模拟社交媒体对话。
请评估哪组更真实自然。

=== 组 X ===
{fmt(x)}

=== 组 Y ===
{fmt(y)}

评估维度（每项1-5分）：
1. emotion_evolution - 情感演化合理性
2. role_differentiation - 角色差异化
3. crisis_response - 危机响应真实性
4. naturalness - 整体自然度

JSON回答：
```json
{{"x_scores":{{"emotion_evolution":N,"role_differentiation":N,"crisis_response":N,"naturalness":N}},
"y_scores":{{"emotion_evolution":N,"role_differentiation":N,"crisis_response":N,"naturalness":N}},
"winner":"X或Y或tie","reasoning":"一句话理由"}}
```"""

    try:
        resp = _llm_chat_with_retry(
            client,
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 + judge_id * 0.15,  # 不同温度 → 不同评委风格
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        result = json.loads(_clean(resp.choices[0].message.content))
        if flip:
            result["a_scores"] = result.pop("y_scores", {})
            result["b_scores"] = result.pop("x_scores", {})
            w = result.get("winner", "tie")
            result["winner"] = "B" if w == "X" else ("A" if w == "Y" else "tie")
        else:
            result["a_scores"] = result.pop("x_scores", {})
            result["b_scores"] = result.pop("y_scores", {})
            w = result.get("winner", "tie")
            result["winner"] = "A" if w == "X" else ("B" if w == "Y" else "tie")
        result["judge_id"] = judge_id
        return result
    except Exception as e:
        return {"error": str(e), "winner": "tie", "judge_id": judge_id}


# ============== 模拟运行 ==============
def run_sim(client, agents, total_rounds, use_wm, topic, inject_events, seed):
    random.seed(seed)
    tmp = tempfile.mkdtemp(prefix=f"llm_{'B' if use_wm else 'A'}_")
    engine = WorldStateEngine(sim_dir=tmp, use_llm=False)
    history, posts, recent = [], [], []
    label = f"{C.G}B{C.RST}" if use_wm else f"{C.R}A{C.RST}"

    for rnd in range(total_rounds):
        evt_text = ""
        if inject_events and rnd in inject_events:
            evt = inject_events[rnd]
            with open(engine.injected_events_path, 'w', encoding='utf-8') as f:
                json.dump([evt], f, ensure_ascii=False)
            evt_text = evt["description"]

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

        actions = []
        for ag in agents:
            if random.random() > ag.activity_level:
                continue
            ws_prompt = ""
            if use_wm:
                ws_prompt = build_world_state_prompt(ws_data,
                    agent_role={"entity_type": ag.entity_type, "stance": ag.stance})
            post = llm_post(client, ag, rnd, topic, recent, ws_prompt, evt_text)
            posts.append({"round": rnd, "agent_id": ag.agent_id, "agent_name": ag.name,
                          "entity_type": ag.entity_type, "stance": ag.stance,
                          "content": post, "has_ws": bool(ws_prompt)})
            recent.append(f"[{ag.name}]: {post}")
            if len(recent) > 12:
                recent = recent[-12:]
            actions.append({"action_type": "CREATE_POST", "agent_id": ag.agent_id,
                            "agent_name": ag.name, "action_args": {"content": post}})

        new_state, events = engine.update_state(rnd, actions)
        sv = new_state.get_state_vector()
        history.append({"round": rnd, "state": sv, "n": len(actions)})
        print(f"    {label} R{rnd:02d} p={sv['panic_level']:.2f} t={sv['trust_level']:.2f} n={len(actions)}"
              f"{'  ⚡' + evt_text[:15] if evt_text else ''}")

    shutil.rmtree(tmp, ignore_errors=True)
    return history, posts


# ============== 分析 ==============
def eval_sentiments(client, posts):
    for p in posts:
        sent = llm_sentiment(client, p["content"], p["agent_name"])
        p["sent_ok"] = sent is not None
        p["sentiment"] = sent if sent is not None else 0.0
    return posts


def sent_trajectory(posts, rounds):
    traj = []
    for r in range(rounds):
        rp = [p["sentiment"] for p in posts if p["round"] == r and p.get("sent_ok", True)]
        traj.append(sum(rp) / len(rp) if rp else 0.0)
    return traj


def diversity(posts, rounds):
    stds = []
    for r in range(rounds):
        ss = [p["sentiment"] for p in posts if p["round"] == r and p.get("sent_ok", True)]
        if len(ss) >= 2:
            m = sum(ss) / len(ss)
            stds.append(math.sqrt(sum((s - m) ** 2 for s in ss) / len(ss)))
    return sum(stds) / len(stds) if stds else 0.0


def crisis_shift(posts, crisis_round):
    pre = [p["sentiment"] for p in posts if p["round"] == crisis_round - 1 and p.get("sent_ok", True)]
    post = [p["sentiment"] for p in posts if p["round"] in (crisis_round + 1, crisis_round + 2) and p.get("sent_ok", True)]
    if pre and post:
        return sum(post) / len(post) - sum(pre) / len(pre)
    return 0.0


def recovery_shift(posts, intervention_round):
    pre = [p["sentiment"] for p in posts if p["round"] in (intervention_round - 1, intervention_round) and p.get("sent_ok", True)]
    post = [p["sentiment"] for p in posts if p["round"] in (intervention_round + 1, intervention_round + 2) and p.get("sent_ok", True)]
    if pre and post:
        return sum(post) / len(post) - sum(pre) / len(pre)
    return 0.0


def _judge_failed(judgment: Dict[str, Any]) -> bool:
    winner = judgment.get("winner")
    reasoning = str(judgment.get("reasoning", "") or "").strip()
    a_scores = judgment.get("a_scores", {})
    b_scores = judgment.get("b_scores", {})
    return winner == "tie" and not reasoning and not a_scores and not b_scores


def assess_run_quality(posts_a, posts_b, judgments):
    all_posts = posts_a + posts_b
    post_error_count = sum(1 for p in all_posts if str(p.get("content", "")).startswith("[ERR:"))
    sentiment_fail_count = sum(1 for p in all_posts if not p.get("sent_ok", True))
    judge_fail_count = sum(1 for j in judgments if _judge_failed(j))
    total_posts = max(1, len(all_posts))

    post_error_rate = post_error_count / total_posts
    sentiment_fail_rate = sentiment_fail_count / total_posts
    is_valid = (
        post_error_rate <= MAX_POST_ERROR_RATE
        and sentiment_fail_rate <= MAX_SENTIMENT_FAIL_RATE
        and judge_fail_count <= MAX_JUDGE_FAIL_COUNT
    )
    return {
        "is_valid": is_valid,
        "post_error_rate": post_error_rate,
        "sentiment_fail_rate": sentiment_fail_rate,
        "judge_fail_count": judge_fail_count,
    }


def sentiment_stability(traj):
    """情感轨迹平滑度（反转次数比率，越低越稳定）"""
    if len(traj) < 3:
        return 0.0
    diffs = [traj[i+1] - traj[i] for i in range(len(traj)-1)]
    changes = sum(1 for i in range(len(diffs)-1) if diffs[i] * diffs[i+1] < 0)
    return changes / max(1, len(diffs) - 1)


# ============== 主流程 ==============
def main():
    if sys.platform == 'win32':
        os.system('')

    print(f"\n{C.BOLD}{C.P}{'═' * 72}{C.RST}")
    print(f"{C.BOLD}{C.P}  NexusMind World Model — Large-Scale LLM Validation{C.RST}")
    print(f"{C.BOLD}{C.P}  {len(SCENARIOS)} topics × 10 agents × {TOTAL_ROUNDS} rounds × {len(SEEDS)} seeds × {NUM_JUDGES} judges{C.RST}")
    print(f"{C.BOLD}{C.P}{'═' * 72}{C.RST}")
    print(f"  {C.DIM}LLM: {Config.LLM_MODEL_NAME} @ {Config.LLM_BASE_URL}{C.RST}")

    client = create_client()

    all_results = []  # 每个 (scenario, seed) 的结果

    for sc_idx, scenario in enumerate(SCENARIOS):
        print(f"\n{'═' * 72}")
        print(f"  {C.BOLD}{C.CY}SCENARIO {sc_idx+1}/{len(SCENARIOS)}: {scenario['name']}{C.RST}")
        print(f"  {C.DIM}{scenario['topic']}{C.RST}")
        print(f"{'═' * 72}")

        crisis_rnd = scenario["crisis"]["round"]
        interv_rnd = scenario["intervention"]["round"]
        inject = {crisis_rnd: scenario["crisis"]["event"],
                  interv_rnd: scenario["intervention"]["event"]}

        for seed in SEEDS:
            print(f"\n  {C.BOLD}--- Seed {seed} ---{C.RST}")
            run_result = None

            for attempt in range(MAX_QUALITY_RETRIES + 1):
                if attempt > 0:
                    print(f"  {C.Y}[QualityRetry] Retry {attempt}/{MAX_QUALITY_RETRIES} for {scenario['name']} seed={seed}{C.RST}")

                # Run A
                print(f"  {C.R}Group A (no WM):{C.RST}")
                _, posts_a = run_sim(client, scenario["agents"], TOTAL_ROUNDS,
                                    False, scenario["topic"], inject, seed)
                # Run B
                print(f"  {C.G}Group B (with WM):{C.RST}")
                _, posts_b = run_sim(client, scenario["agents"], TOTAL_ROUNDS,
                                    True, scenario["topic"], inject, seed)

                # Sentiment evaluation
                print(f"  {C.DIM}Scoring sentiments ({len(posts_a)+len(posts_b)} posts)...{C.RST}")
                posts_a = eval_sentiments(client, posts_a)
                posts_b = eval_sentiments(client, posts_b)

                traj_a = sent_trajectory(posts_a, TOTAL_ROUNDS)
                traj_b = sent_trajectory(posts_b, TOTAL_ROUNDS)

                # Quantitative metrics
                m = {
                    "avg_sent":   (sum(traj_a)/len(traj_a), sum(traj_b)/len(traj_b)),
                    "diversity":  (diversity(posts_a, TOTAL_ROUNDS), diversity(posts_b, TOTAL_ROUNDS)),
                    "crisis":     (abs(crisis_shift(posts_a, crisis_rnd)),
                                   abs(crisis_shift(posts_b, crisis_rnd))),
                    "recovery":   (recovery_shift(posts_a, interv_rnd),
                                   recovery_shift(posts_b, interv_rnd)),
                    "stability":  (sentiment_stability(traj_a), sentiment_stability(traj_b)),
                }

                # Multiple judges
                print(f"  {C.DIM}Blind evaluation ({NUM_JUDGES} judges)...{C.RST}")
                judgments = []
                for j in range(NUM_JUDGES):
                    jresult = llm_judge(client, posts_a, posts_b, j)
                    judgments.append(jresult)
                    w = jresult.get("winner", "?")
                    print(f"    Judge {j+1}: {C.G if w=='B' else (C.R if w=='A' else C.Y)}{w}{C.RST}"
                          f" — {jresult.get('reasoning', '')[:50]}")

                quality = assess_run_quality(posts_a, posts_b, judgments)
                if not quality["is_valid"]:
                    print(
                        f"  {C.Y}[QualityWarning]{C.RST} invalid run: "
                        f"post_err={quality['post_error_rate']:.1%}, "
                        f"sent_fail={quality['sentiment_fail_rate']:.1%}, "
                        f"judge_fail={quality['judge_fail_count']}"
                    )

                # Majority vote
                votes = Counter(j.get("winner") for j in judgments)
                majority = votes.most_common(1)[0][0] if votes else "tie"

                run_result = {
                    "scenario": scenario["name"],
                    "seed": seed,
                    "metrics": m,
                    "judgments": judgments,
                    "majority_winner": majority,
                    "posts_a": posts_a,
                    "posts_b": posts_b,
                    "traj_a": traj_a,
                    "traj_b": traj_b,
                    "quality": quality,
                }

                if quality["is_valid"] or attempt == MAX_QUALITY_RETRIES:
                    break

            all_results.append(run_result)

    # ============== 汇总 ==============
    print(f"\n\n{'═' * 72}")
    print(f"  {C.BOLD}{C.CY}AGGREGATE RESULTS{C.RST}")
    print(f"  {C.DIM}{len(all_results)} scenario-seed pairs evaluated{C.RST}")
    print(f"{'═' * 72}")

    # 1) 定量指标汇总
    metric_labels = {
        "avg_sent":  ("Avg Sentiment",      "closer to 0 = balanced"),
        "diversity": ("Behavior Diversity",  "higher = better differentiation"),
        "crisis":    ("Crisis Sensitivity",  "higher = more responsive"),
        "recovery":  ("Recovery Response",   "more positive = better"),
        "stability": ("Sentiment Stability", "lower = smoother trajectory"),
    }

    valid_results = [r for r in all_results if r.get("quality", {}).get("is_valid", True)]
    if not valid_results:
        valid_results = all_results
    if len(valid_results) != len(all_results):
        print(f"\n  {C.Y}[QualityGate]{C.RST} Using {len(valid_results)}/{len(all_results)} valid runs for aggregate scoring")

    metric_wins = {k: {"A": 0, "B": 0, "tie": 0} for k in metric_labels}

    for res in valid_results:
        for k in metric_labels:
            va, vb = res["metrics"][k]
            if k == "avg_sent":
                # 更接近 0 = 更平衡
                better = "B" if abs(vb) < abs(va) - 0.03 else ("A" if abs(va) < abs(vb) - 0.03 else "tie")
            elif k == "stability":
                # 更低 = 更平滑
                better = "B" if vb < va - 0.02 else ("A" if va < vb - 0.02 else "tie")
            elif k == "recovery":
                better = "B" if vb > va + 0.03 else ("A" if va > vb + 0.03 else "tie")
            else:
                better = "B" if vb > va + 0.03 else ("A" if va > vb + 0.03 else "tie")
            metric_wins[k][better] += 1

    print(f"\n  {C.BOLD}Quantitative Metrics (across {len(valid_results)} runs):{C.RST}")
    print(f"  {'─' * 60}")
    total_b_pts = 0
    total_pts = 0
    for k, (label, desc) in metric_labels.items():
        w = metric_wins[k]
        total = w["A"] + w["B"] + w["tie"]
        b_pts = w["B"] + w["tie"] * 0.5
        total_b_pts += b_pts
        total_pts += total
        pct = b_pts / total * 100 if total else 0
        color = C.G if pct >= 60 else (C.R if pct < 40 else C.Y)
        print(f"    {label:24s} A={w['A']} B={w['B']} tie={w['tie']}  "
              f"{color}{pct:5.0f}% B{C.RST}  {C.DIM}({desc}){C.RST}")

    # 2) 评委投票汇总
    print(f"\n  {C.BOLD}LLM Judge Votes (across {len(valid_results)} runs × {NUM_JUDGES} judges):{C.RST}")
    print(f"  {'─' * 60}")

    all_votes = Counter()
    majority_votes = Counter()
    dim_scores = {"a": Counter(), "b": Counter()}

    for res in valid_results:
        majority_votes[res["majority_winner"]] += 1
        for j in res["judgments"]:
            all_votes[j.get("winner", "tie")] += 1
            for dim in ["emotion_evolution", "role_differentiation", "crisis_response", "naturalness"]:
                a_s = j.get("a_scores", {}).get(dim, 0)
                b_s = j.get("b_scores", {}).get(dim, 0)
                if isinstance(a_s, (int, float)) and isinstance(b_s, (int, float)):
                    dim_scores["a"][dim] += a_s
                    dim_scores["b"][dim] += b_s

    total_votes = sum(all_votes.values())
    b_vote_pts = all_votes.get("B", 0) + all_votes.get("tie", 0) * 0.5
    total_b_pts += b_vote_pts
    total_pts += total_votes

    print(f"    Individual votes: A={all_votes.get('A',0)}  B={all_votes.get('B',0)}  tie={all_votes.get('tie',0)}"
          f"  ({b_vote_pts/total_votes*100:.0f}% B)" if total_votes else "")
    print(f"    Majority decisions: A={majority_votes.get('A',0)}  B={majority_votes.get('B',0)}  tie={majority_votes.get('tie',0)}")

    n_judges_total = max(1, sum(dim_scores["a"].values()) // max(1, len(dim_scores["a"])))
    print(f"\n    {C.BOLD}Average Judge Scores (sum across all evaluations):{C.RST}")
    for dim in ["emotion_evolution", "role_differentiation", "crisis_response", "naturalness"]:
        a_total = dim_scores["a"].get(dim, 0)
        b_total = dim_scores["b"].get(dim, 0)
        winner = C.G + "◀B" + C.RST if b_total > a_total else (C.R + "◀A" + C.RST if a_total > b_total else "tie")
        print(f"      {dim:28s}  A={a_total:5.0f}  B={b_total:5.0f}  {winner}")

    # 3) 总分
    overall_pct = total_b_pts / total_pts * 100 if total_pts else 0
    print(f"\n{'═' * 72}")
    print(f"  {C.BOLD}{C.CY}FINAL SCORE{C.RST}")
    print(f"{'═' * 72}")
    print(f"  B points: {total_b_pts:.1f} / {total_pts}")

    bar_len = 40
    filled = int(overall_pct / 100 * bar_len)
    color = C.G if overall_pct >= 60 else (C.Y if overall_pct >= 40 else C.R)
    print(f"\n  Win Rate: {color}{'█' * filled}{'░' * (bar_len - filled)} {overall_pct:.0f}%{C.RST}")

    if overall_pct >= 60:
        print(f"\n  {C.G}{C.BOLD}✓ VALIDATED: World model consistently improves real LLM agent behavior.{C.RST}")
    elif overall_pct >= 40:
        print(f"\n  {C.Y}{C.BOLD}~ INCONCLUSIVE: Mixed results — world model shows partial benefit.{C.RST}")
    else:
        print(f"\n  {C.R}{C.BOLD}✗ NOT VALIDATED: World model does not clearly help real LLM agents.{C.RST}")

    # 保存结果
    out_path = os.path.join(os.path.dirname(__file__), "llm_validation_large_result.json")
    save_data = {
        "model": Config.LLM_MODEL_NAME,
        "scenarios": [s["name"] for s in SCENARIOS],
        "seeds": SEEDS,
        "total_rounds": TOTAL_ROUNDS,
        "num_judges": NUM_JUDGES,
        "metric_wins": {k: dict(v) for k, v in metric_wins.items()},
        "judge_votes": dict(all_votes),
        "majority_votes": dict(majority_votes),
        "overall_win_rate": overall_pct,
        "valid_run_count": len(valid_results),
        "detailed_results": [
            {
                "scenario": r["scenario"], "seed": r["seed"],
                "metrics": {k: {"a": v[0], "b": v[1]} for k, v in r["metrics"].items()},
                "majority_winner": r["majority_winner"],
                "quality": r.get("quality", {}),
                "judgments": [{"winner": j.get("winner"), "reasoning": j.get("reasoning", ""),
                               "a_scores": j.get("a_scores", {}), "b_scores": j.get("b_scores", {})}
                              for j in r["judgments"]],
                "traj_a": r["traj_a"], "traj_b": r["traj_b"],
            }
            for r in all_results
        ],
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n  {C.DIM}Full results saved to: {out_path}{C.RST}\n")


if __name__ == "__main__":
    main()
