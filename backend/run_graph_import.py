"""
轻量版图谱导入：直接用 Cypher 写入 Neo4j，绕过 Graphiti。
将模拟的 Agent 活动（发帖、评论、转发等）写入图谱，与已有的知识图谱实体关联。
"""
import json
import os
import sys
from datetime import datetime

from neo4j import GraphDatabase

# === 配置 ===
SIM_DIR = os.path.join('uploads', 'simulations', 'sim_07a7f2769964')
GRAPH_ID = 'nexusmind_7c4508debf6246d1'
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_AUTH = ('neo4j', 'neo4jneo4j')
SKIP_ACTIONS = {'DO_NOTHING', 'INTERVIEW'}  # 不写入的 action 类型
BATCH_SIZE = 50  # 每批写入条数


def load_actions(sim_dir: str) -> list:
    """从 actions.jsonl 读取所有有意义的 Agent 行为"""
    actions = []
    for platform in ('twitter', 'reddit'):
        log_path = os.path.join(sim_dir, platform, 'actions.jsonl')
        if not os.path.exists(log_path):
            continue
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # 跳过事件类型和无意义行为
                    if 'event_type' in data:
                        continue
                    action_type = data.get('action_type', '')
                    if action_type in SKIP_ACTIONS:
                        continue
                    data['platform'] = platform
                    actions.append(data)
                except json.JSONDecodeError:
                    continue
    return actions


def import_to_neo4j(actions: list):
    """批量写入 Neo4j"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    # 1. 创建约束和索引（幂等）
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT sim_action_id IF NOT EXISTS
            FOR (a:SimAction) REQUIRE a.uid IS UNIQUE
        """)
        session.run("""
            CREATE INDEX sim_action_round IF NOT EXISTS
            FOR (a:SimAction) ON (a.round)
        """)
        session.run("""
            CREATE INDEX sim_agent_name IF NOT EXISTS
            FOR (a:SimAgent) ON (a.name)
        """)

    # 2. 批量写入 Agent 节点 + Action 节点 + 关系
    total = 0
    with driver.session() as session:
        for i in range(0, len(actions), BATCH_SIZE):
            batch = actions[i:i + BATCH_SIZE]
            params = []
            for act in batch:
                content = ''
                args = act.get('action_args', {})
                if isinstance(args, dict):
                    content = args.get('content', '') or args.get('post_content', '') or ''
                params.append({
                    'uid': f"{GRAPH_ID}_{act.get('platform','?')}_{act.get('round',0)}_{act.get('agent_id',0)}_{act.get('action_type','')}",
                    'agent_name': act.get('agent_name', ''),
                    'action_type': act.get('action_type', ''),
                    'content': content[:500],  # 截断过长内容
                    'round': act.get('round', 0),
                    'platform': act.get('platform', ''),
                    'timestamp': act.get('timestamp', ''),
                    'graph_id': GRAPH_ID,
                })

            session.run("""
                UNWIND $batch AS row
                MERGE (agent:SimAgent {name: row.agent_name, graph_id: row.graph_id})
                MERGE (action:SimAction {uid: row.uid})
                SET action.action_type = row.action_type,
                    action.content = row.content,
                    action.round = row.round,
                    action.platform = row.platform,
                    action.timestamp = row.timestamp,
                    action.graph_id = row.graph_id
                MERGE (agent)-[:PERFORMED]->(action)
            """, batch=params)

            total += len(batch)
            print(f"  写入 {total}/{len(actions)} 条...")

    # 3. 将 SimAgent 与已有的知识图谱实体关联（按名称匹配）
    with driver.session() as session:
        result = session.run("""
            MATCH (sa:SimAgent {graph_id: $gid})
            MATCH (entity) WHERE entity.name = sa.name
              AND NOT entity:SimAgent AND NOT entity:SimAction
            MERGE (sa)-[:CORRESPONDS_TO]->(entity)
            RETURN count(*) as linked
        """, gid=GRAPH_ID)
        linked = result.single()['linked']
        print(f"  关联到已有图谱实体: {linked} 条")

    # 4. 统计
    with driver.session() as session:
        r = session.run("""
            MATCH (a:SimAction {graph_id: $gid})
            RETURN count(a) as actions,
                   count(DISTINCT a.platform) as platforms,
                   max(a.round) as max_round
        """, gid=GRAPH_ID)
        stats = r.single()
        print(f"\n=== 导入完成 ===")
        print(f"  SimAction 节点: {stats['actions']}")
        print(f"  平台数: {stats['platforms']}")
        print(f"  最大轮次: {stats['max_round']}")

    driver.close()


if __name__ == '__main__':
    print(f"sim_dir: {os.path.abspath(SIM_DIR)}")
    actions = load_actions(SIM_DIR)
    print(f"读取到 {len(actions)} 条有意义的 Agent 行为")
    if actions:
        import_to_neo4j(actions)
    else:
        print("没有可导入的数据")
    print("Done!")
