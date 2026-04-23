"""
量化评估 API 路由

提供模拟结果的量化分析接口，所有接口为只读操作。
"""

import traceback

from flask import jsonify, request

from . import evaluation_bp
from ..services.evaluation import SimulationEvaluator
from ..utils.logger import get_logger

logger = get_logger('nexusmind.api.evaluation')


@evaluation_bp.route('/simulations', methods=['GET'])
def list_evaluable():
    """列出所有可评估的模拟"""
    try:
        sims = SimulationEvaluator.list_evaluable_simulations()
        return jsonify({"success": True, "data": sims})
    except Exception as e:
        logger.error(f"列出可评估模拟失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/report', methods=['GET'])
def get_report(simulation_id: str):
    """
    获取完整评估报告

    返回情感演化、行为多样性、世界状态摘要、影响力排行等指标。
    """
    try:
        evaluator = SimulationEvaluator(simulation_id)
        report = evaluator.generate_report()
        return jsonify({"success": True, "data": report.to_dict()})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"生成评估报告失败: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/sentiment', methods=['GET'])
def get_sentiment(simulation_id: str):
    """
    获取情感时序数据

    返回每轮的正面/负面/中性情感占比，以及情感摘要统计。
    """
    try:
        evaluator = SimulationEvaluator(simulation_id)
        data = evaluator.get_sentiment_timeline()
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"获取情感时序失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/diversity', methods=['GET'])
def get_diversity(simulation_id: str):
    """
    获取行为多样性指标

    返回动作类型分布、基尼系数、活跃Agent比例等。
    """
    try:
        evaluator = SimulationEvaluator(simulation_id)
        data = evaluator.get_behavior_diversity()
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"获取行为多样性失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/state-evolution', methods=['GET'])
def get_state_evolution(simulation_id: str):
    """
    获取世界状态演化摘要

    返回6维状态的峰值/谷值、波动率、关键转折点等。
    """
    try:
        evaluator = SimulationEvaluator(simulation_id)
        data = evaluator.get_state_evolution()
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"获取世界状态演化失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/benchmark', methods=['GET'])
def get_benchmark(simulation_id: str):
    """
    获取 Benchmark 三级评分（Tier A/B/C）

    扫描 benchmark/ 目录下与该 simulation_id 匹配的 benchmark_score*.json，
    返回各 Tier 的分数供前端展示。
    """
    import os, json, glob
    from ..config import Config

    try:
        benchmark_base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "benchmark")
        
        # 扫描所有 case 目录下的 benchmark_score*.json
        tiers = {}
        pattern = os.path.join(benchmark_base, "case_*", "benchmark_score*.json")
        for fpath in glob.glob(pattern):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tier = data.get("knowledge_tier", "A (Full)")
                scores = data.get("scores", {})
                tiers[tier] = {
                    "total": scores.get("total", 0),
                    "grade": scores.get("grade", ""),
                    "TCS": scores.get("TCS", 0),
                    "TPH": scores.get("TPH", 0),
                    "KAC": scores.get("KAC", 0),
                    "EOA": scores.get("EOA", 0),
                    "case_name": data.get("case_name", ""),
                    "file": os.path.basename(fpath),
                }
            except Exception:
                continue
        
        # 如果没有找到任何 benchmark 数据，也尝试读取 simulation 目录下的 state.json 获取 knowledge_level
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        knowledge_level = "full"
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            knowledge_level = state_data.get("knowledge_level", "full")
        
        # 计算 Information Premium
        tier_a_score = tiers.get("A (Full)", {}).get("total", 0)
        tier_c_score = tiers.get("C (Blind)", {}).get("total", 0)
        info_premium = tier_a_score - tier_c_score if tier_a_score and tier_c_score else None

        return jsonify({
            "success": True,
            "data": {
                "tiers": tiers,
                "current_knowledge_level": knowledge_level,
                "information_premium": info_premium,
            }
        })
    except Exception as e:
        logger.error(f"获取 Benchmark 评分失败: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@evaluation_bp.route('/<simulation_id>/influence', methods=['GET'])
def get_influence(simulation_id: str):
    """
    获取影响力分析

    返回Agent影响力排行、信息集中度等。
    """
    try:
        evaluator = SimulationEvaluator(simulation_id)
        data = evaluator.get_influence_analysis()
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"获取影响力分析失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
