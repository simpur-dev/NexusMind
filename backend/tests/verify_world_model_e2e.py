"""
端到端验证：世界模型是否真正注入到 Agent 的 LLM prompt 中
"""
import json, os, sys, asyncio, tempfile, shutil
from string import Template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.world_state import WorldStateSnapshot
from run_parallel_simulation import (
    read_world_state, build_world_state_prompt, patch_oasis_environment,
)
import run_parallel_simulation as rps


def main():
    tmp = tempfile.mkdtemp()
    
    # ============ Step 1: 后端写入世界状态 ============
    print("=" * 60)
    print("Step 1: 模拟后端写入世界状态文件")
    print("=" * 60)
    
    ws = WorldStateSnapshot(
        round_num=3, timestamp="t",
        attention_level=0.85, panic_level=0.6, trust_level=0.3,
        polarization_level=0.5, risk_level=0.7, stability_level=0.2,
    )
    payload = ws.to_dict()
    payload["state_summary_text"] = ws.get_state_summary_text()
    payload["recent_events"] = [
        {"event_type": "heat_spike", "description": "舆论热度急升，多方关注", "severity": 0.8},
        {"event_type": "trust_drop", "description": "公众信任度显著下降", "severity": 0.6},
    ]
    
    ws_path = os.path.join(tmp, "world_state_current.json")
    with open(ws_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  写入: {ws_path}")
    print(f"  状态: attention={ws.attention_level}, panic={ws.panic_level}, trust={ws.trust_level}")
    
    # ============ Step 2: 子进程读取 ============
    print()
    print("=" * 60)
    print("Step 2: 子进程读取世界状态文件")
    print("=" * 60)
    
    ws_data = read_world_state(tmp)
    assert ws_data is not None, "读取失败!"
    print(f"  读取成功: round_num={ws_data['round_num']}")
    
    world_prompt = build_world_state_prompt(ws_data)
    rps._current_world_state_prompt = world_prompt
    print(f"  生成的世界状态 prompt ({len(world_prompt)} chars):")
    for line in world_prompt.strip().split("\n"):
        print(f"    | {line}")
    
    # ============ Step 3: Monkey-patch 注入验证 ============
    print()
    print("=" * 60)
    print("Step 3: 验证 monkey-patch 注入到 Agent 环境 prompt")
    print("=" * 60)
    
    patch_oasis_environment()
    
    from oasis.social_agent.agent_environment import SocialEnvironment
    
    # 创建最小 mock
    env = SocialEnvironment.__new__(SocialEnvironment)
    env.env_template = Template(
        "Posts: $posts_env | Followers: $followers_env | Follows: $follows_env | Groups: $groups_env"
    )
    
    async def fake_posts():
        return "No new posts"
    async def fake_followers():
        return "5 followers"
    async def fake_follows():
        return "3 follows"
    async def fake_groups():
        return "No groups"
    
    env.get_posts_env = fake_posts
    env.get_followers_env = fake_followers
    env.get_follows_env = fake_follows
    env.get_group_env = fake_groups
    
    result = asyncio.run(env.to_text_prompt())
    
    print(f"  Agent 看到的完整 prompt ({len(result)} chars):")
    print()
    for line in result.strip().split("\n"):
        print(f"    | {line}")
    
    # ============ Step 4: 验证结果 ============
    print()
    print("=" * 60)
    print("Step 4: 验证闭环")
    print("=" * 60)
    
    checks = {
        "包含背景标题": "Background" in result,
        "包含量化指标(attention)": "0.85" in result,
        "包含恐慌数据": "0.6" in result or "恐慌" in result,
        "包含事件: 舆论热度急升": "舆论热度急升" in result,
        "包含事件: 信任度下降": "信任度显著下降" in result,
        "无指令式语言": "Your actions should" not in result,
    }
    
    all_pass = True
    for desc, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        print("  🎯 结论: 世界模型 ★已经★ 注入到 Agent 的 LLM prompt 中")
        print("     每轮 Agent 决策时都会看到全局环境状态和重大事件")
        print("     LLM 会基于这些信息调整行为（如恐慌高→更激进发言）")
    else:
        print("  ⚠️ 部分检查未通过，需要排查")
    
    shutil.rmtree(tmp, ignore_errors=True)
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
