"""
世界状态引擎演示脚本

模拟一个「校园食品安全事件」5 轮舆论演化：
  Round 1: 有人发帖曝光食堂卫生问题
  Round 2: 更多学生跟帖吐槽，负面情绪蔓延
  Round 3: 恐慌加剧，谣言出现，转发量飙升
  Round 4: 校方发布官方声明回应，媒体报道
  Round 5: 舆论逐渐平息，信任回升
"""

import os
import sys
import json
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.world_state import WorldStateEngine, WorldStateSnapshot


def create_demo_actions():
    """创建 5 轮逼真的模拟动作数据"""
    
    rounds = {
        1: [
            # Round 1: 曝光事件
            {"action_type": "CREATE_POST", "agent_id": 1, "agent_name": "张同学", 
             "action_args": {"content": "刚在食堂吃到虫子了！恶心死了，大家小心第二食堂的麻辣烫"}},
            {"action_type": "CREATE_POST", "agent_id": 2, "agent_name": "李同学", 
             "action_args": {"content": "今天的菜品质量还不错，推荐一楼的番茄炒蛋"}},
            {"action_type": "COMMENT", "agent_id": 3, "agent_name": "王同学", 
             "action_args": {"content": "真的吗？我也觉得最近食堂越来越差了"}},
            {"action_type": "LIKE", "agent_id": 4, "agent_name": "赵同学", "action_args": {}},
            {"action_type": "COMMENT", "agent_id": 5, "agent_name": "陈同学", 
             "action_args": {"content": "支持曝光！应该让学校重视这个问题"}},
        ],
        2: [
            # Round 2: 负面情绪蔓延
            {"action_type": "CREATE_POST", "agent_id": 6, "agent_name": "刘同学", 
             "action_args": {"content": "食堂卫生问题不是第一次了！上次我朋友也吃出异物，学校根本不管"}},
            {"action_type": "CREATE_POST", "agent_id": 7, "agent_name": "孙同学", 
             "action_args": {"content": "强烈不满！交了那么多钱伙食费，结果吃的是什么东西？失望！"}},
            {"action_type": "COMMENT", "agent_id": 1, "agent_name": "张同学", 
             "action_args": {"content": "我已经拍了照片取证了，大家一起维权！愤怒！"}},
            {"action_type": "REPOST", "agent_id": 8, "agent_name": "吴同学", "action_args": {}},
            {"action_type": "REPOST", "agent_id": 9, "agent_name": "周同学", "action_args": {}},
            {"action_type": "COMMENT", "agent_id": 10, "agent_name": "郑同学", 
             "action_args": {"content": "食堂承包商是不是有问题？应该查查他们的资质"}},
            {"action_type": "CREATE_POST", "agent_id": 11, "agent_name": "黄同学", 
             "action_args": {"content": "我觉得大家不要太激动，先等学校调查结果"}},
            {"action_type": "LIKE", "agent_id": 12, "agent_name": "林同学", "action_args": {}},
        ],
        3: [
            # Round 3: 恐慌加剧，谣言出现
            {"action_type": "CREATE_POST", "agent_id": 13, "agent_name": "匿名用户A", 
             "action_args": {"content": "听说好几个同学吃了食堂的东西食物中毒住院了！太危险了！大家千万别去食堂！"}},
            {"action_type": "CREATE_POST", "agent_id": 14, "agent_name": "匿名用户B", 
             "action_args": {"content": "据说食堂用的是过期食材，有人已经报警了！恐慌！混乱！"}},
            {"action_type": "REPOST", "agent_id": 1, "agent_name": "张同学", "action_args": {}},
            {"action_type": "REPOST", "agent_id": 3, "agent_name": "王同学", "action_args": {}},
            {"action_type": "REPOST", "agent_id": 6, "agent_name": "刘同学", "action_args": {}},
            {"action_type": "REPOST", "agent_id": 7, "agent_name": "孙同学", "action_args": {}},
            {"action_type": "REPOST", "agent_id": 8, "agent_name": "吴同学", "action_args": {}},
            {"action_type": "COMMENT", "agent_id": 15, "agent_name": "马同学", 
             "action_args": {"content": "这是谣言还是真的？有没有官方回应？担心害怕"}},
            {"action_type": "COMMENT", "agent_id": 10, "agent_name": "郑同学", 
             "action_args": {"content": "学校到底什么态度？这么多天了一点回应都没有！不满"}},
            {"action_type": "CREATE_POST", "agent_id": 16, "agent_name": "何同学", 
             "action_args": {"content": "我选择去校外吃了，食堂太不安全了，大家都走吧"}},
        ],
        4: [
            # Round 4: 官方回应
            {"action_type": "CREATE_POST", "agent_id": 100, "agent_name": "校方发言人", 
             "action_args": {"content": "关于食堂卫生问题的官方声明：学校已成立调查组，通报结果将于明日公布。声明 通知 措施 政策"}},
            {"action_type": "CREATE_POST", "agent_id": 101, "agent_name": "校园媒体", 
             "action_args": {"content": "校方回应食堂事件：已暂停涉事档口运营，卫生部门已介入检查。官方 回应 声明"}},
            {"action_type": "COMMENT", "agent_id": 11, "agent_name": "黄同学", 
             "action_args": {"content": "官方终于回应了，支持学校的处理，希望尽快解决"}},
            {"action_type": "COMMENT", "agent_id": 5, "agent_name": "陈同学", 
             "action_args": {"content": "总算有个态度了，继续关注后续结果"}},
            {"action_type": "COMMENT", "agent_id": 1, "agent_name": "张同学", 
             "action_args": {"content": "声明太笼统了，希望公布具体检查数据和处罚结果"}},
            {"action_type": "LIKE", "agent_id": 12, "agent_name": "林同学", "action_args": {}},
            {"action_type": "LIKE", "agent_id": 15, "agent_name": "马同学", "action_args": {}},
            {"action_type": "CREATE_POST", "agent_id": 14, "agent_name": "匿名用户B", 
             "action_args": {"content": "之前的消息可能有误，等官方调查结果吧，辟谣 澄清"}},
        ],
        5: [
            # Round 5: 趋于平息
            {"action_type": "CREATE_POST", "agent_id": 100, "agent_name": "校方发言人", 
             "action_args": {"content": "调查结果公告：涉事档口已整改，承包方已更换，全面提升食堂安全标准。感谢同学们的监督。官方 公告 改善 解决"}},
            {"action_type": "COMMENT", "agent_id": 11, "agent_name": "黄同学", 
             "action_args": {"content": "处理得不错，希望以后能保持。支持 信任"}},
            {"action_type": "COMMENT", "agent_id": 3, "agent_name": "王同学", 
             "action_args": {"content": "终于解决了，希望食堂越来越好"}},
            {"action_type": "CREATE_POST", "agent_id": 2, "agent_name": "李同学", 
             "action_args": {"content": "今天新食堂开放了，大家可以去尝尝，味道还不错！改善 稳定"}},
            {"action_type": "LIKE", "agent_id": 4, "agent_name": "赵同学", "action_args": {}},
            {"action_type": "LIKE", "agent_id": 5, "agent_name": "陈同学", "action_args": {}},
            {"action_type": "LIKE", "agent_id": 8, "agent_name": "吴同学", "action_args": {}},
        ],
    }
    
    return rounds


def print_state_bar(label: str, value: float, width: int = 30):
    """打印状态条"""
    filled = int(value * width)
    bar = "█" * filled + "░" * (width - filled)
    # 颜色标记
    if value < 0.3:
        color = "\033[92m"  # green
    elif value < 0.6:
        color = "\033[93m"  # yellow
    else:
        color = "\033[91m"  # red
    reset = "\033[0m"
    print(f"  {label:12s} {color}{bar}{reset} {value:.3f}")


def print_state(state: WorldStateSnapshot):
    """美化打印世界状态"""
    print(f"\n  {'─' * 52}")
    print_state_bar("关注度", state.attention_level)
    print_state_bar("恐慌程度", state.panic_level)
    # trust: 反向着色（高=绿，低=红）
    trust_val = state.trust_level
    filled = int(trust_val * 30)
    bar = "█" * filled + "░" * (30 - filled)
    if trust_val > 0.6:
        color = "\033[92m"
    elif trust_val > 0.3:
        color = "\033[93m"
    else:
        color = "\033[91m"
    reset = "\033[0m"
    print(f"  {'信任度':12s} {color}{bar}{reset} {trust_val:.3f}")
    print_state_bar("极化程度", state.polarization_level)
    print_state_bar("风险等级", state.risk_level)
    # stability: 反向着色
    stab_val = state.stability_level
    filled = int(stab_val * 30)
    bar = "█" * filled + "░" * (30 - filled)
    if stab_val > 0.6:
        color = "\033[92m"
    elif stab_val > 0.3:
        color = "\033[93m"
    else:
        color = "\033[91m"
    reset = "\033[0m"
    print(f"  {'稳定性':12s} {color}{bar}{reset} {stab_val:.3f}")
    
    print(f"\n  活跃Agent: {state.active_agent_count} | "
          f"发帖: {state.total_posts} | 评论: {state.total_comments} | "
          f"转发: {state.total_reposts} | 点赞: {state.total_likes}")
    
    if state.top_keywords:
        print(f"  热词: {', '.join(state.top_keywords[:8])}")
    
    sd = state.sentiment_distribution
    print(f"  情感分布: 正面 {sd.get('positive', 0):.0%} | "
          f"负面 {sd.get('negative', 0):.0%} | 中性 {sd.get('neutral', 0):.0%}")


def main():
    print("\n" + "=" * 60)
    print("  🌍 NexusMind 世界状态引擎演示")
    print("  📋 场景: 校园食品安全事件舆论演化 (5轮)")
    print("=" * 60)
    
    # 创建临时目录
    demo_dir = tempfile.mkdtemp(prefix="nexusmind_demo_")
    print(f"\n  📁 数据目录: {demo_dir}")
    
    # 初始化引擎（关闭 LLM，纯规则驱动）
    engine = WorldStateEngine(sim_dir=demo_dir, use_llm=False)
    
    rounds_data = create_demo_actions()
    all_events = []
    
    scenario_desc = {
        1: "🔍 有学生曝光食堂卫生问题，引发初步关注",
        2: "😤 更多学生跟帖吐槽，负面情绪开始蔓延",
        3: "🚨 恐慌加剧！未经证实的谣言出现，转发量飙升",
        4: "📢 校方发布官方声明回应，媒体介入报道",
        5: "🕊️ 事件逐步解决，舆论趋于平息",
    }
    
    for round_num in range(1, 6):
        actions = rounds_data[round_num]
        
        print(f"\n\n{'━' * 60}")
        print(f"  ▶ 第 {round_num} 轮 — {scenario_desc[round_num]}")
        print(f"{'━' * 60}")
        
        # 显示本轮关键动作
        print(f"\n  📝 本轮动作 ({len(actions)} 条):")
        for a in actions:
            atype = a["action_type"]
            name = a.get("agent_name", "?")
            content = a.get("action_args", {}).get("content", "")
            if content:
                print(f"     [{name}] {atype}: {content[:50]}...")
            else:
                print(f"     [{name}] {atype}")
        
        # 更新世界状态
        new_state, events = engine.update_state(round_num, actions)
        
        print(f"\n  📊 世界状态:")
        print_state(new_state)
        
        if events:
            print(f"\n  ⚡ 检测到 {len(events)} 个事件:")
            for evt in events:
                severity_bar = "🔴" if evt.severity > 0.5 else "🟡" if evt.severity > 0.3 else "🟢"
                print(f"     {severity_bar} [{evt.event_type}] {evt.description} (严重度: {evt.severity:.2f})")
            all_events.extend(events)
        else:
            print(f"\n  ✅ 本轮无异常事件")
    
    # 总结
    print(f"\n\n{'=' * 60}")
    print(f"  📈 模拟总结")
    print(f"{'=' * 60}")
    
    print(f"\n  共 {len(engine.state_history)} 轮状态记录")
    print(f"  共 {len(all_events)} 个关键事件")
    
    print(f"\n  状态演化趋势:")
    print(f"  {'轮次':>4s} | {'关注度':>6s} | {'恐慌':>6s} | {'信任':>6s} | {'极化':>6s} | {'风险':>6s} | {'稳定':>6s}")
    print(f"  {'─' * 52}")
    for s in engine.state_history:
        print(f"  {s.round_num:>4d} | {s.attention_level:>6.3f} | {s.panic_level:>6.3f} | "
              f"{s.trust_level:>6.3f} | {s.polarization_level:>6.3f} | {s.risk_level:>6.3f} | "
              f"{s.stability_level:>6.3f}")
    
    if all_events:
        print(f"\n  事件时间线:")
        for evt in all_events:
            print(f"  Round {evt.round_num}: [{evt.event_type}] {evt.description}")
    
    # 因果图谱
    cg = engine.causal_graph
    edges = cg.edges
    print(f"\n  🔗 因果图谱: {len(edges)} 条因果边")
    relation_symbols = {
        "triggered": "──▶",
        "amplified": "══▶",
        "suppressed": "──✕",
        "correlated": "···▶",
    }
    for edge in edges:
        src = cg._events_cache.get(edge.source_event_id)
        tgt = cg._events_cache.get(edge.target_event_id)
        src_desc = f"R{src.round_num}:{src.event_type}" if src else edge.source_event_id[:12]
        tgt_desc = f"R{tgt.round_num}:{tgt.event_type}" if tgt else edge.target_event_id[:12]
        sym = relation_symbols.get(edge.relation_type, "-->")
        print(f"     {src_desc} {sym} {tgt_desc}  ({edge.relation_type}, strength={edge.strength:.2f})")
        print(f"       └ {edge.evidence}")
    
    # 因果链追踪示例
    if all_events:
        first_evt = all_events[0]
        chains = cg.get_causal_chain(first_evt.event_id)
        if chains:
            print(f"\n  📍 因果链追踪 (从 \"{first_evt.description[:30]}...\" 出发):")
            for i, chain in enumerate(chains):
                print(f"     链{i+1} (strength={chain.total_strength:.3f}): {chain.description}")
    
    # 验证持久化
    state_file = os.path.join(demo_dir, "world_state_history.jsonl")
    events_file = os.path.join(demo_dir, "events.jsonl")
    
    print(f"\n  💾 持久化文件:")
    if os.path.exists(state_file):
        with open(state_file) as f:
            lines = f.readlines()
        print(f"     world_state_history.jsonl: {len(lines)} 条记录")
    if os.path.exists(events_file):
        with open(events_file) as f:
            lines = f.readlines()
        print(f"     events.jsonl: {len(lines)} 条记录")
    causal_file = os.path.join(demo_dir, "causal_edges.jsonl")
    if os.path.exists(causal_file):
        with open(causal_file) as f:
            lines = f.readlines()
        print(f"     causal_edges.jsonl: {len(lines)} 条记录")
    
    print(f"\n  🎯 当前状态文本摘要:")
    print(f"  {engine.current_state.get_state_summary_text()}")
    
    # 清理
    shutil.rmtree(demo_dir, ignore_errors=True)
    print(f"\n{'=' * 60}")
    print(f"  ✅ 演示完成！")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
