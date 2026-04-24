"""
预测分支运行 API
桥接 ForecastRun → SimulationManager → SimulationRunner，
将"预测分支"概念映射到已有模拟引擎

独立于 simulation.py，避免原文件继续膨胀
"""

import threading
import traceback
from datetime import datetime
from flask import request, jsonify

from . import forecast_bp
from ..config import Config
from ..models.project import ProjectManager
from ..models.material import MaterialManager
from ..models.baseline import BaselineManager
from ..models.forecast_run import ForecastRun, ForecastRunManager
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner
from ..utils.logger import get_logger

logger = get_logger("nexusmind.api.forecast")


# ============================================================
# 预测分支生命周期
# ============================================================

@forecast_bp.route("/run/create", methods=["POST"])
def create_forecast_run():
    """
    创建预测分支并关联底层 Simulation

    请求 JSON：
        {
            "project_id": "proj_xxx",
            "baseline_id": "bl_xxx",
            "branch_type": "base",                // 可选 base | intervention_a | ...
            "branch_label": "基准预测",            // 可选
            "parent_run_id": "run_xxx",           // 可选
            "forecast_horizon_hours": 168,        // 可选
            "intervention_plan": {...}            // 可选
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        project_id = data.get("project_id")
        baseline_id = data.get("baseline_id")

        if not project_id or not baseline_id:
            return jsonify({"success": False, "error": "请提供 project_id 和 baseline_id"}), 400

        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        baseline = BaselineManager.get_baseline(project_id, baseline_id)
        if not baseline:
            return jsonify({"success": False, "error": f"基线不存在: {baseline_id}"}), 404

        graph_id = baseline.graph_id or project.graph_id
        if not graph_id:
            return jsonify({"success": False, "error": "项目尚未构建图谱"}), 400

        # 1. 创建 ForecastRun 元数据
        run = ForecastRunManager.create_run(
            project_id,
            baseline_id,
            branch_type=data.get("branch_type", "base"),
            branch_label=data.get("branch_label"),
            parent_run_id=data.get("parent_run_id"),
            forecast_horizon_hours=data.get("forecast_horizon_hours", 168),
            intervention_plan=data.get("intervention_plan"),
        )

        # 2. 创建底层 Simulation（每个 run 独立，不复用旧模拟）
        manager = SimulationManager()
        sim_state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=True,
            enable_reddit=True,
            baseline_id=baseline_id,
            run_id=run.run_id,
        )

        # 3. 回写 simulation_id 到 ForecastRun
        run.simulation_id = sim_state.simulation_id
        run.graph_id = graph_id
        ForecastRunManager.save_run(run)

        # 4. 更新项目 active_run_id
        project.active_run_id = run.run_id
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "run": run.to_dict(),
                "simulation": sim_state.to_simple_dict(),
            },
        })

    except Exception as e:
        logger.error(f"创建预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/prepare", methods=["POST"])
def prepare_forecast_run(run_id: str):
    """
    准备预测分支的模拟环境

    与 /api/simulation/prepare 类似，但输入来源改为基线关联的材料文本，
    而不是项目全量 extracted_text.txt

    请求 JSON（可选）：
        {
            "entity_types": [...],
            "use_llm_for_profiles": true,
            "parallel_profile_count": 5,
            "force_regenerate": false
        }
    """
    from ..models.task import TaskManager, TaskStatus
    from ..services.entity_reader import EntityReader

    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404

        if not run.simulation_id:
            return jsonify({"success": False, "error": "预测分支尚未关联 simulation"}), 400

        project = ProjectManager.get_project(run.project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {run.project_id}"}), 404

        data = request.get_json(silent=True) or {}
        force_regenerate = data.get("force_regenerate", False)

        manager = SimulationManager()
        sim_state = manager.get_simulation(run.simulation_id)
        if not sim_state:
            return jsonify({"success": False, "error": f"模拟不存在: {run.simulation_id}"}), 404

        # 检查是否已经准备好
        from .simulation import _check_simulation_prepared
        if not force_regenerate:
            is_prepared, info = _check_simulation_prepared(run.simulation_id)
            if is_prepared:
                return jsonify({
                    "success": True,
                    "data": {
                        "run_id": run_id,
                        "simulation_id": run.simulation_id,
                        "status": "ready",
                        "message": "已有完成的准备工作",
                        "already_prepared": True,
                        "prepare_info": info,
                    },
                })

        # 构造 document_text —— 优先使用基线关联材料，fallback 到项目全文
        baseline = BaselineManager.get_baseline(run.project_id, run.baseline_id) if run.baseline_id else None
        if baseline and baseline.based_on_material_ids:
            document_text = MaterialManager.get_combined_text(run.project_id, baseline.based_on_material_ids)
        else:
            document_text = ProjectManager.get_extracted_text(run.project_id) or ""

        if not document_text:
            return jsonify({"success": False, "error": "没有可用的材料文本"}), 400

        simulation_requirement = project.simulation_requirement or ""
        if not simulation_requirement:
            return jsonify({"success": False, "error": "项目缺少模拟需求描述"}), 400

        # 实体类型
        entity_types_list = data.get("entity_types")
        if not entity_types_list and project.ontology:
            types_raw = project.ontology.get("entity_types", [])
            entity_types_list = [t["name"] for t in types_raw if isinstance(t, dict) and t.get("name")]

        use_llm = data.get("use_llm_for_profiles", True)
        parallel_count = data.get("parallel_profile_count", 5)

        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="forecast_prepare",
            metadata={"simulation_id": run.simulation_id, "run_id": run_id, "project_id": run.project_id},
        )

        # 更新 ForecastRun 状态
        run.status = "preparing"
        ForecastRunManager.save_run(run)
        sim_state.status = SimulationStatus.PREPARING
        manager._save_simulation_state(sim_state)

        def _run_prepare():
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0, message="开始准备...")

                def _progress(stage, progress, message, **kw):
                    stage_weights = {
                        "reading": (0, 20),
                        "generating_profiles": (20, 70),
                        "generating_config": (70, 90),
                        "copying_scripts": (90, 100),
                    }
                    start, end = stage_weights.get(stage, (0, 100))
                    total_prog = int(start + (end - start) * progress / 100)
                    task_manager.update_task(task_id, progress=total_prog, message=f"[{stage}] {message}")

                result_state = manager.prepare_simulation(
                    simulation_id=run.simulation_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    defined_entity_types=entity_types_list,
                    use_llm_for_profiles=use_llm,
                    progress_callback=_progress,
                    parallel_profile_count=parallel_count,
                )

                if result_state.status == SimulationStatus.FAILED:
                    task_manager.fail_task(task_id, result_state.error or "准备失败")
                    run.status = "failed"
                    run.error = result_state.error
                    ForecastRunManager.save_run(run)
                    return

                task_manager.complete_task(task_id, result=result_state.to_simple_dict())
                # 不立即改 run.status，留给 start 来触发

            except Exception as exc:
                logger.error(f"预测分支 prepare 失败: {exc}")
                task_manager.fail_task(task_id, str(exc))
                run.status = "failed"
                run.error = str(exc)
                ForecastRunManager.save_run(run)

        thread = threading.Thread(target=_run_prepare, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "run_id": run_id,
                "simulation_id": run.simulation_id,
                "task_id": task_id,
                "status": "preparing",
                "message": "准备任务已启动",
                "already_prepared": False,
            },
        })

    except Exception as e:
        logger.error(f"准备预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/start", methods=["POST"])
def start_forecast_run(run_id: str):
    """
    启动预测分支的模拟运行

    请求 JSON（可选）：
        {
            "platform": "parallel",
            "max_rounds": 20,
            "enable_graph_memory_update": false,
            "force": false,
            "resume": false
        }
    """
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404
        if not run.simulation_id:
            return jsonify({"success": False, "error": "请先 prepare"}), 400

        data = request.get_json(silent=True) or {}

        manager = SimulationManager()
        sim_state = manager.get_simulation(run.simulation_id)
        if not sim_state:
            return jsonify({"success": False, "error": f"模拟不存在: {run.simulation_id}"}), 404

        # 检查准备状态
        from .simulation import _check_simulation_prepared
        is_prepared, _ = _check_simulation_prepared(run.simulation_id)
        if not is_prepared:
            return jsonify({"success": False, "error": "模拟未准备好，请先 prepare"}), 400

        # 如果状态不是 READY，尝试恢复
        if sim_state.status != SimulationStatus.READY:
            sim_state.status = SimulationStatus.READY
            manager._save_simulation_state(sim_state)

        platform = data.get("platform", "parallel")
        max_rounds = data.get("max_rounds")
        enable_graph_memory = data.get("enable_graph_memory_update", False)
        force = data.get("force", False)
        resume = data.get("resume", False)

        if max_rounds is not None:
            max_rounds = int(max_rounds)

        start_round = 0
        if resume:
            rs = SimulationRunner.get_run_state(run.simulation_id)
            if rs and rs.current_round > 0:
                start_round = rs.current_round

        if force and not resume:
            SimulationRunner.cleanup_simulation_logs(run.simulation_id)

        # 启动模拟
        result = SimulationRunner.start_simulation(
            simulation_id=run.simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory,
            start_round=start_round,
        )

        # 更新 ForecastRun 状态
        run.status = "running"
        ForecastRunManager.save_run(run)

        return jsonify({
            "success": True,
            "data": {
                "run_id": run_id,
                "simulation_id": run.simulation_id,
                "runner_status": result.get("runner_status", "running") if isinstance(result, dict) else "running",
                "message": "预测分支已启动",
            },
        })

    except Exception as e:
        logger.error(f"启动预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/recalibrate", methods=["POST"])
def recalibrate_forecast_run(run_id: str):
    """
    现实校准：新材料进入后，对世界状态做事实校准并创建新预测分支

    逻辑：
    1. 找到原分支关联的 simulation
    2. 用新基线的事实数据生成 reality_patch
    3. 将 patch 应用到 WorldStateEngine
    4. 创建新的 ForecastRun（原分支保持不变）

    请求 JSON：
        {
            "new_baseline_id": "bl_yyy",
            "branch_label": "校准后预测 v2"       // 可选
        }
    """
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404

        data = request.get_json(silent=True) or {}
        new_baseline_id = data.get("new_baseline_id")
        if not new_baseline_id:
            return jsonify({"success": False, "error": "请提供 new_baseline_id"}), 400

        new_baseline = BaselineManager.get_baseline(run.project_id, new_baseline_id)
        if not new_baseline:
            return jsonify({"success": False, "error": f"基线不存在: {new_baseline_id}"}), 404

        old_baseline = BaselineManager.get_baseline(run.project_id, run.baseline_id)

        # 计算基线 diff
        diff = {}
        if old_baseline:
            diff = BaselineManager.diff_baselines(run.project_id, run.baseline_id, new_baseline_id)

        # 生成 reality_patch（基于 diff 和新基线内容）
        reality_patch = _build_reality_patch(new_baseline, diff)

        # 对原分支的 WorldStateEngine 执行 patch
        if run.simulation_id:
            import os
            sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, run.simulation_id)
            if os.path.exists(sim_dir):
                from ..services.world_state import WorldStateEngine
                engine = WorldStateEngine(sim_dir, use_llm=False)
                engine.apply_reality_patch(reality_patch)

        # 创建新的 ForecastRun 作为校准后分支
        new_run = ForecastRunManager.create_run(
            run.project_id,
            new_baseline_id,
            branch_type="recalibrated",
            branch_label=data.get("branch_label", f"校准自 {run.run_id}"),
            parent_run_id=run.run_id,
            forecast_horizon_hours=run.forecast_horizon_hours,
        )

        # 为新分支创建底层 Simulation
        project = ProjectManager.get_project(run.project_id)
        graph_id = run.graph_id or (project.graph_id if project else None)
        if graph_id:
            manager = SimulationManager()
            sim_state = manager.create_simulation(
                project_id=run.project_id,
                graph_id=graph_id,
                enable_twitter=True,
                enable_reddit=True,
                baseline_id=new_baseline_id,
                run_id=new_run.run_id,
            )
            new_run.simulation_id = sim_state.simulation_id
            new_run.graph_id = graph_id
            ForecastRunManager.save_run(new_run)

        # 更新原分支状态标记
        run.status = "superseded"
        ForecastRunManager.save_run(run)

        # 更新项目 active_run
        if project:
            project.active_run_id = new_run.run_id
            project.current_baseline_id = new_baseline_id
            ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "old_run_id": run_id,
                "new_run": new_run.to_dict(),
                "reality_patch": reality_patch,
                "baseline_diff_summary": diff,
                "message": "校准完成，已创建新预测分支，请对新分支执行 prepare → start",
            },
        })

    except Exception as e:
        logger.error(f"校准预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/compare", methods=["POST"])
def compare_forecast_runs():
    """
    对比多个预测分支

    请求 JSON：
        {
            "project_id": "proj_xxx",
            "run_ids": ["run_aaa", "run_bbb"]
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        project_id = data.get("project_id")
        run_ids = data.get("run_ids", [])

        if not project_id or len(run_ids) < 2:
            return jsonify({"success": False, "error": "请提供 project_id 和至少 2 个 run_ids"}), 400

        meta_compare = ForecastRunManager.compare_runs(project_id, run_ids)

        # 尝试获取各分支的世界状态趋势
        import os
        trends = {}
        for rid in run_ids:
            run = ForecastRunManager.get_run(project_id, rid)
            if run and run.simulation_id:
                sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, run.simulation_id)
                if os.path.exists(sim_dir):
                    from ..services.world_state import WorldStateEngine
                    engine = WorldStateEngine(sim_dir, use_llm=False)
                    trends[rid] = {
                        var: engine.get_state_trend(var)
                        for var in ["attention_level", "panic_level", "trust_level",
                                    "polarization_level", "risk_level", "stability_level"]
                    }

        return jsonify({
            "success": True,
            "data": {
                "meta": meta_compare,
                "state_trends": trends,
            },
        })

    except Exception as e:
        logger.error(f"对比预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/status", methods=["GET"])
def get_forecast_run_status(run_id: str):
    """获取预测分支运行状态"""
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404

        sim_info = None
        runner_info = None
        if run.simulation_id:
            manager = SimulationManager()
            sim_state = manager.get_simulation(run.simulation_id)
            if sim_state:
                sim_info = sim_state.to_simple_dict()

            rs = SimulationRunner.get_run_state(run.simulation_id)
            if rs:
                runner_info = {
                    "runner_status": rs.runner_status.value if hasattr(rs.runner_status, "value") else str(rs.runner_status),
                    "current_round": rs.current_round,
                    "max_rounds": rs.max_rounds,
                }

                # 模拟完成时同步更新 ForecastRun 状态
                if rs.runner_status.value in ("completed", "stopped") and run.status == "running":
                    run.status = "completed"
                    run.completed_at = datetime.now().isoformat()
                    ForecastRunManager.save_run(run)

            # prepare 完成时同步更新（simulation 已 ready 但 run 还在 preparing）
            if sim_state and sim_state.status.value == "ready" and run.status == "preparing":
                run.status = "ready"
                ForecastRunManager.save_run(run)
            elif sim_state and sim_state.status.value == "failed" and run.status == "preparing":
                run.status = "failed"
                run.error = sim_state.error
                ForecastRunManager.save_run(run)

        return jsonify({
            "success": True,
            "data": {
                "run": run.to_dict(),
                "simulation": sim_info,
                "runner": runner_info,
            },
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 干预动作模板 & 结构化决策简报
# ============================================================

@forecast_bp.route("/interventions", methods=["GET"])
def list_intervention_templates():
    """返回全部干预动作模板"""
    try:
        from ..services.intervention_library import InterventionLibrary
        lib = InterventionLibrary()
        return jsonify({"success": True, "data": lib.list_all()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecast_bp.route("/run/<run_id>/evaluate-interventions", methods=["POST"])
def evaluate_interventions(run_id: str):
    """
    评估一组干预动作对当前预测分支的组合效果

    请求 JSON：
        {
            "action_ids": ["act_preliminary_response", "act_suspend_involved"]
        }
    """
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404

        data = request.get_json(silent=True) or {}
        action_ids = data.get("action_ids", [])
        if not action_ids:
            return jsonify({"success": False, "error": "请提供 action_ids"}), 400

        # 获取当前世界状态
        current_state = _get_current_world_state(run)

        from ..services.intervention_library import InterventionLibrary
        lib = InterventionLibrary()
        result = lib.evaluate_intervention_plan(action_ids, current_state)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"评估干预方案失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/decision-brief", methods=["GET"])
def get_decision_brief(run_id: str):
    """
    获取预测分支的结构化决策简报

    输出 §5.6.3 完整 DecisionBrief，包含：
    - current_diagnosis
    - top_risks / top_opportunities
    - recommended_actions（InterventionLibrary 推荐的 Top-3）
    - action_alternatives
    - supporting_evidence / monitoring_signals
    - no_action_risk / forecast_paths
    """
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404
        if not run.simulation_id:
            return jsonify({"success": False, "error": "预测分支尚未关联模拟"}), 400
        if run.status not in ("running", "completed"):
            return jsonify({
                "success": False,
                "error": f"预测分支状态为 '{run.status}'，需要先完成 prepare → start 流程才能获取决策简报",
            }), 400

        from ..services.simulation_insight_service import SimulationInsightService
        service = SimulationInsightService(run.simulation_id)

        # 支持传入 baseline_id 以差异化简报内容
        baseline_id = request.args.get("baseline_id")
        baseline_context = None
        logger.info(f"[决策简报] run_id={run_id}, baseline_id={baseline_id}, all_args={dict(request.args)}")
        if baseline_id:
            try:
                from ..models.baseline import BaselineManager
                bl = BaselineManager.get_baseline(run.project_id, baseline_id)
                if bl:
                    baseline_context = bl.to_dict()
                    logger.info(f"[决策简报] 加载基线成功: stage={baseline_context.get('current_stage')}, risks={len(baseline_context.get('current_risks', []))}")
                else:
                    logger.warning(f"[决策简报] 基线不存在: project={run.project_id}, baseline={baseline_id}")
            except Exception as be:
                logger.warning(f"加载基线 {baseline_id} 失败，将忽略: {be}")

        brief = service.get_structured_decision_brief(baseline_context=baseline_context)

        return jsonify({"success": True, "data": brief})

    except Exception as e:
        logger.error(f"获取决策简报失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@forecast_bp.route("/run/<run_id>/recommend-actions", methods=["GET"])
def recommend_actions(run_id: str):
    """
    根据当前世界状态推荐最合适的 Top-N 干预动作

    Query params:
        max_results: 返回数量（默认 3）
    """
    try:
        run = _find_run(run_id)
        if not run:
            return jsonify({"success": False, "error": f"预测分支不存在: {run_id}"}), 404
        if run.status not in ("running", "completed"):
            return jsonify({
                "success": False,
                "error": f"预测分支状态为 '{run.status}'，需要先完成 prepare → start 流程",
            }), 400

        max_results = int(request.args.get("max_results", 3))
        current_state = _get_current_world_state(run)

        from ..services.intervention_library import InterventionLibrary
        lib = InterventionLibrary()
        recommended = lib.recommend_actions(current_state, max_results=max_results)

        return jsonify({"success": True, "data": {"current_state": current_state, "recommended": recommended}})

    except Exception as e:
        logger.error(f"推荐干预动作失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============================================================
# 内部工具函数
# ============================================================

def _get_current_world_state(run: ForecastRun) -> dict:
    """从 ForecastRun 关联的 simulation 获取最新 6 维世界状态"""
    import os
    default_state = {
        "attention_level": 0.3, "panic_level": 0.3, "trust_level": 0.5,
        "polarization_level": 0.3, "risk_level": 0.3, "stability_level": 0.6,
    }
    if not run.simulation_id:
        return default_state
    sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, run.simulation_id)
    if not os.path.exists(sim_dir):
        return default_state
    try:
        from ..services.world_state import WorldStateEngine
        engine = WorldStateEngine(sim_dir, use_llm=False)
        cs = engine.current_state
        if cs:
            return cs.get_state_vector()
    except Exception as e:
        logger.warning(f"读取世界状态失败: {e}")
    return default_state


def _find_run(run_id: str) -> ForecastRun | None:
    """遍历所有项目查找 run（run_id 全局唯一）"""
    from ..models.project import ProjectManager
    for project in ProjectManager.list_projects():
        run = ForecastRunManager.get_run(project.project_id, run_id)
        if run:
            return run
    return None


def _build_reality_patch(baseline, diff: dict) -> dict:
    """
    根据新基线和 diff 构建 reality_patch。

    reality_patch 结构：
        {
            "state_overrides": { "trust_level": 0.4, ... },
            "events_to_inject": [ {"description": "...", "severity": ...} ],
            "new_facts": ["...", ...],
        }
    """
    patch: dict = {
        "state_overrides": {},
        "events_to_inject": [],
        "new_facts": [],
    }

    # 从新基线的风险判断状态调整
    if baseline.current_risks:
        risk_count = len(baseline.current_risks)
        if risk_count >= 3:
            patch["state_overrides"]["risk_level"] = min(1.0, 0.3 + risk_count * 0.1)

    # 新增的确认事实
    facts_diff = diff.get("confirmed_facts_diff", {})
    if isinstance(facts_diff, dict):
        added_facts = facts_diff.get("added", [])
        patch["new_facts"] = added_facts
        if added_facts:
            patch["events_to_inject"].append({
                "event_type": "reality_update",
                "description": f"现实校准：新增 {len(added_facts)} 条确认事实",
                "severity": min(1.0, len(added_facts) * 0.15),
            })

    # 阶段变化
    stage_change = diff.get("stage_change", {})
    if isinstance(stage_change, dict) and stage_change.get("before") != stage_change.get("after"):
        patch["events_to_inject"].append({
            "event_type": "stage_transition",
            "description": f"事件阶段从「{stage_change.get('before', '未知')}」变为「{stage_change.get('after', '未知')}」",
            "severity": 0.6,
        })

    return patch
