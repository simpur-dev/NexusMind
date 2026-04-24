"""检查模拟种子材料中的信息泄漏"""
import json

SIM_DIR = r"e:\NexusMind\backend\uploads\simulations\sim_656a9425082e"

# 后续阶段才应出现的关键词（P2-P5 的信息）
LATE_STAGE_KEYWORDS = [
    "撤销处分", "二审", "判决", "复核", "百余处", "不规范",
    "问责", "整改", "通报", "PTSD", "胜诉", "驳回",
    "暂停招生", "书面检查", "制度反思", "维持原判",
]

# 1. 检查初始帖子
print("=" * 60)
print("1. 初始帖子信息泄漏检查")
print("=" * 60)
config = json.load(open(f"{SIM_DIR}/simulation_config.json", "r", encoding="utf-8"))
posts = config.get("initial_posts", [])
for i, p in enumerate(posts):
    content = p.get("content", "")
    name = p.get("publisher_entity_name", "?")
    found = [kw for kw in LATE_STAGE_KEYWORDS if kw in content]
    if found:
        print(f"  [泄漏] 帖子{i} ({name}): {found}")
        print(f"         片段: {content[:120]}...")
    else:
        print(f"  [安全] 帖子{i} ({name})")

# 2. 检查 Agent 人设
print("\n" + "=" * 60)
print("2. Agent 人设信息泄漏检查")
print("=" * 60)
profiles = json.load(open(f"{SIM_DIR}/reddit_profiles.json", "r", encoding="utf-8"))
leak_count = 0
for p in profiles:
    persona = p.get("persona", "")
    bio = p.get("bio", "")
    combined = persona + " " + bio
    name = p.get("name", p.get("username", "?"))
    found_persona = [kw for kw in LATE_STAGE_KEYWORDS if kw in persona]
    found_bio = [kw for kw in LATE_STAGE_KEYWORDS if kw in bio]
    if found_persona or found_bio:
        leak_count += 1
        if found_persona:
            print(f"  [泄漏-persona] {name}: {found_persona}")
        if found_bio:
            print(f"  [泄漏-bio]     {name}: {found_bio}")

print(f"\n  总计: {leak_count}/{len(profiles)} 个 Agent 人设包含后续阶段信息")

# 3. 统计泄漏严重程度
print("\n" + "=" * 60)
print("3. 泄漏严重程度评估")
print("=" * 60)
total_leak_chars = 0
for p in profiles:
    persona = p.get("persona", "") + " " + p.get("bio", "")
    for kw in LATE_STAGE_KEYWORDS:
        if kw in persona:
            # 找到关键词周围的上下文
            idx = persona.find(kw)
            total_leak_chars += len(persona[max(0,idx-50):idx+50])

print(f"  泄漏信息量约: {total_leak_chars} 字符")
print(f"  泄漏 Agent 占比: {leak_count}/{len(profiles)} = {leak_count/len(profiles)*100:.0f}%")

if leak_count > len(profiles) * 0.5:
    print("\n  [严重] 超过50%的Agent从R1就知道事件结局")
    print("  结论: 99.3分中存在显著信息泄漏，Benchmark分数被高估")
elif leak_count > 0:
    print("\n  [中等] 部分Agent存在信息泄漏")
else:
    print("\n  [安全] 无信息泄漏")
