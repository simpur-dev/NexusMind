"""
NexusMind Benchmark 评分脚本

用法：
  cd NexusMind
  python benchmark/scoring.py benchmark/case_01_wuhan_university_library

输入：
  - <case_dir>/reference_data.json    参考真值
  - <case_dir>/evaluation_result.json 系统评估输出

输出：
  - TCS / TPH / KAC / EOA 各项分数
  - 综合 Benchmark Score
"""

import json
import sys
import os


# ============================================================
# 权重配置
# ============================================================
WEIGHTS = {
    "TCS": 0.35,
    "TPH": 0.25,
    "KAC": 0.20,
    "EOA": 0.20,
}


# ============================================================
# TCS：趋势一致性（Trend Consistency Score）
# ============================================================
def compute_tcs(reference: dict, evaluation: dict) -> dict:
    """
    比较参考阶段情绪方向 vs 模拟阶段情绪方向。
    
    evaluation_result.json 中需要有：
      "phase_sentiment_directions": ["negative_rising", "negative_peak", ...]
    
    评分规则：
      完全一致 = 1.0, 大体接近 = 0.5, 明显不符 = 0.0
    """
    ref_dirs = reference.get("sentiment_direction_sequence", [])
    sim_dirs = evaluation.get("phase_sentiment_directions", [])

    if not ref_dirs:
        return {"score": 0, "detail": "参考数据缺少 sentiment_direction_sequence", "matched": []}

    if not sim_dirs:
        return {"score": 0, "detail": "评估结果缺少 phase_sentiment_directions，请先人工标注", "matched": []}

    # 方向相似度映射
    similar_pairs = {
        ("negative_rising", "negative_peak"),
        ("negative_peak", "negative_rising"),
        ("negative_peak", "negative_sustained"),
        ("negative_sustained", "negative_peak"),
        ("mixed", "negative_secondary"),
        ("negative_secondary", "mixed"),
        ("neutral_declining", "mixed"),
        ("mixed", "neutral_declining"),
    }

    matches = []
    n = min(len(ref_dirs), len(sim_dirs))
    for i in range(n):
        r, s = ref_dirs[i], sim_dirs[i]
        if r == s:
            matches.append({"phase": i + 1, "ref": r, "sim": s, "score": 1.0})
        elif (r, s) in similar_pairs:
            matches.append({"phase": i + 1, "ref": r, "sim": s, "score": 0.5})
        else:
            matches.append({"phase": i + 1, "ref": r, "sim": s, "score": 0.0})

    raw = sum(m["score"] for m in matches) / n if n > 0 else 0
    return {"score": round(raw * 100, 1), "detail": f"{n} 阶段对比", "matched": matches}


# ============================================================
# TPH：转折点命中率（Turning Point Hit Rate）
# ============================================================
def compute_tph(reference: dict, evaluation: dict) -> dict:
    """
    检查参考转折点是否在模拟中被命中。
    
    evaluation_result.json 中需要有：
      "turning_points_hit": [
        {"tp_id": "T1", "hit": "same_phase" | "adjacent_phase" | "missed"}
      ]
    
    评分规则：
      same_phase = 1.0, adjacent_phase = 0.5, missed = 0.0
    """
    ref_tps = reference.get("turning_points_top3", [])
    sim_hits = evaluation.get("turning_points_hit", [])

    if not ref_tps:
        return {"score": 0, "detail": "参考数据缺少 turning_points_top3", "matched": []}

    if not sim_hits:
        return {"score": 0, "detail": "评估结果缺少 turning_points_hit，请先人工标注", "matched": []}

    hit_map = {h["tp_id"]: h["hit"] for h in sim_hits}
    score_map = {"same_phase": 1.0, "adjacent_phase": 0.5, "missed": 0.0}

    matches = []
    for tp in ref_tps:
        tid = tp["tp_id"]
        hit = hit_map.get(tid, "missed")
        s = score_map.get(hit, 0.0)
        matches.append({"tp_id": tid, "description": tp["description"], "hit": hit, "score": s})

    raw = sum(m["score"] for m in matches) / len(matches) if matches else 0
    return {"score": round(raw * 100, 1), "detail": f"{len(ref_tps)} 转折点", "matched": matches}


# ============================================================
# KAC：关键主体覆盖率（Key Actor Coverage）
# ============================================================
def compute_kac(reference: dict, evaluation: dict) -> dict:
    """
    检查 high importance 主体是否在图谱/Agent/报告中出现。
    
    evaluation_result.json 中需要有：
      "actor_coverage": [
        {"actor_id": "A1", "in_graph": true, "in_agent": true, "in_report": true}
      ]
    """
    ref_actors = reference.get("key_actors", [])
    high_actors = [a for a in ref_actors if a.get("importance") == "high"]
    sim_coverage = evaluation.get("actor_coverage", [])

    if not high_actors:
        return {"score": 0, "detail": "参考数据无 high importance 主体", "matched": []}

    if not sim_coverage:
        return {"score": 0, "detail": "评估结果缺少 actor_coverage，请先人工标注", "matched": []}

    cov_map = {c["actor_id"]: c for c in sim_coverage}
    matches = []

    for actor in high_actors:
        aid = actor["actor_id"]
        cov = cov_map.get(aid, {})
        # 按期望维度计算覆盖率
        checks = []
        if actor.get("expected_in_graph"):
            checks.append(cov.get("in_graph", False))
        if actor.get("expected_in_agent"):
            checks.append(cov.get("in_agent", False))
        if actor.get("expected_in_report"):
            checks.append(cov.get("in_report", False))

        hit_rate = sum(checks) / len(checks) if checks else 0
        matches.append({"actor_id": aid, "name": actor["name"], "hit_rate": hit_rate, "detail": cov})

    raw = sum(m["hit_rate"] for m in matches) / len(matches) if matches else 0
    return {"score": round(raw * 100, 1), "detail": f"{len(high_actors)} 高重要性主体", "matched": matches}


# ============================================================
# EOA：事件顺序准确率（Event Order Accuracy）
# ============================================================
def compute_eoa(reference: dict, evaluation: dict) -> dict:
    """
    比较参考事件链与模拟事件链的顺序一致程度。
    
    evaluation_result.json 中需要有：
      "event_order_simulation": ["事件曝光", "媒体报道", ...]
    
    使用 Kendall tau 距离的简化版：逐对比较顺序一致性。
    """
    ref_order = reference.get("event_order_reference", [])
    sim_order = evaluation.get("event_order_simulation", [])

    if not ref_order:
        return {"score": 0, "detail": "参考数据缺少 event_order_reference", "matched": []}

    if not sim_order:
        return {"score": 0, "detail": "评估结果缺少 event_order_simulation，请先人工标注", "matched": []}

    # 找到两个序列中都存在的事件
    common = [e for e in ref_order if e in sim_order]
    if len(common) < 2:
        return {"score": 50, "detail": f"仅 {len(common)} 个共同事件，无法比较顺序", "matched": []}

    # 比较每对事件的相对顺序
    ref_idx = {e: i for i, e in enumerate(ref_order)}
    sim_idx = {e: i for i, e in enumerate(sim_order)}

    concordant = 0
    total = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            a, b = common[i], common[j]
            ref_before = ref_idx[a] < ref_idx[b]
            sim_before = sim_idx[a] < sim_idx[b]
            if ref_before == sim_before:
                concordant += 1
            total += 1

    raw = concordant / total if total > 0 else 0
    return {
        "score": round(raw * 100, 1),
        "detail": f"{concordant}/{total} 对顺序一致（{len(common)} 共同事件）",
        "matched": {"common_events": common, "concordant": concordant, "total_pairs": total},
    }


# ============================================================
# 综合评分
# ============================================================
def compute_benchmark_score(tcs: float, tph: float, kac: float, eoa: float) -> float:
    return round(
        WEIGHTS["TCS"] * tcs +
        WEIGHTS["TPH"] * tph +
        WEIGHTS["KAC"] * kac +
        WEIGHTS["EOA"] * eoa,
        1
    )


def grade(score: float) -> str:
    if score >= 80:
        return "A — 高度接近现实，可作为核心展示案例"
    elif score >= 65:
        return "B — 具备参考价值，可作为补充案例"
    else:
        return "C — 偏差较大，适合消融实验分析"


# ============================================================
# 主流程
# ============================================================
def main():
    if len(sys.argv) < 2:
        print("用法: python benchmark/scoring.py <case_directory>")
        print("示例: python benchmark/scoring.py benchmark/case_01_wuhan_university_library")
        sys.exit(1)

    case_dir = sys.argv[1]
    eval_filename = sys.argv[2] if len(sys.argv) > 2 else "evaluation_result.json"

    ref_path = os.path.join(case_dir, "reference_data.json")
    eval_path = os.path.join(case_dir, eval_filename)

    if not os.path.exists(ref_path):
        print(f"错误：找不到参考数据文件 {ref_path}")
        sys.exit(1)

    if not os.path.exists(eval_path):
        print(f"错误：找不到评估结果文件 {eval_path}")
        print(f"请先运行系统并将评估结果保存到 {eval_path}")
        print(f"或使用人工标注模板填写评分数据。")
        sys.exit(1)

    with open(ref_path, "r", encoding="utf-8-sig") as f:
        reference = json.load(f)

    with open(eval_path, "r", encoding="utf-8-sig") as f:
        evaluation = json.load(f)

    case_name = reference.get("case_name", os.path.basename(case_dir))

    knowledge_tier = evaluation.get("knowledge_tier", "A (Full)")
    
    print("=" * 60)
    print(f"  NexusMind Benchmark 评分")
    print(f"  案例：{case_name}")
    print(f"  知识等级：Tier {knowledge_tier}")
    print("=" * 60)

    # 计算各指标
    tcs_result = compute_tcs(reference, evaluation)
    tph_result = compute_tph(reference, evaluation)
    kac_result = compute_kac(reference, evaluation)
    eoa_result = compute_eoa(reference, evaluation)

    # 综合评分
    total = compute_benchmark_score(
        tcs_result["score"], tph_result["score"],
        kac_result["score"], eoa_result["score"]
    )

    print(f"\n{'─' * 60}")
    print(f"  指标评分")
    print(f"{'─' * 60}")
    print(f"  TCS（趋势一致性）  ：{tcs_result['score']:6.1f} / 100  （权重 35%）")
    print(f"    └ {tcs_result['detail']}")
    print(f"  TPH（转折点命中率）：{tph_result['score']:6.1f} / 100  （权重 25%）")
    print(f"    └ {tph_result['detail']}")
    print(f"  KAC（主体覆盖率）  ：{kac_result['score']:6.1f} / 100  （权重 20%）")
    print(f"    └ {kac_result['detail']}")
    print(f"  EOA（事件顺序准确）：{eoa_result['score']:6.1f} / 100  （权重 20%）")
    print(f"    └ {eoa_result['detail']}")
    print(f"{'─' * 60}")
    print(f"  综合评分：{total:.1f} / 100")
    print(f"  等级：{grade(total)}")
    print(f"{'─' * 60}")

    # 保存详细结果
    result = {
        "case_id": reference.get("case_id"),
        "case_name": case_name,
        "knowledge_tier": knowledge_tier,
        "scores": {
            "TCS": tcs_result["score"],
            "TPH": tph_result["score"],
            "KAC": kac_result["score"],
            "EOA": eoa_result["score"],
            "total": total,
            "grade": grade(total),
        },
        "details": {
            "TCS": tcs_result,
            "TPH": tph_result,
            "KAC": kac_result,
            "EOA": eoa_result,
        },
    }

    eval_stem = os.path.splitext(eval_filename)[0]
    score_suffix = eval_stem.replace("evaluation_result", "").strip("_")
    score_name = f"benchmark_score_{score_suffix}.json" if score_suffix else "benchmark_score.json"
    out_path = os.path.join(case_dir, score_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  详细结果已保存至：{out_path}")


if __name__ == "__main__":
    main()
