"""
滚动预测工作台 API
负责材料追加、基线管理、预测分支管理等面向"事件工作台"的接口
"""

import traceback
from datetime import datetime
from flask import request, jsonify

from . import incident_bp
from ..models.project import ProjectManager
from ..models.material import MaterialManager
from ..models.baseline import BaselineManager
from ..models.forecast_run import ForecastRunManager
from ..services.text_processor import TextProcessor
from ..utils.logger import get_logger

logger = get_logger("nexusmind.api.incident")


# ============================================================
# 项目创建（轻量）
# ============================================================

@incident_bp.route("/project/create", methods=["POST"])
def create_incident_project():
    """
    轻量创建事件工作台项目（不走本体/图谱流程）。
    请求 JSON：{ "name": "...", "simulation_requirement": "..." }
    """
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        requirement = data.get("simulation_requirement", "").strip()
        if not requirement:
            return jsonify({"success": False, "error": "请提供 simulation_requirement"}), 400

        project = ProjectManager.create_project(name=name or requirement[:40])
        project.simulation_requirement = requirement
        project.incident_mode = "rolling_workspace"
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "name": project.name,
            },
        })
    except Exception as e:
        logger.error(f"创建事件项目失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 材料管理
# ============================================================

@incident_bp.route("/project/<project_id>/materials/append", methods=["POST"])
def append_materials(project_id: str):
    """
    向已有项目追加种子材料

    支持两种模式：
      1. 文件上传：form-data，字段 files（多文件）
      2. 手工文本：JSON  {"title": "...", "text": "...", "source_type": "manual", ...}

    公共可选参数（form-data 用同名字段，JSON 直接放顶层）：
      source_type, source_url, source_time, credibility, tags（逗号分隔）
    """
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        added: list = []

        # ── 文件模式 ──
        files = request.files.getlist("files")
        if files and files[0].filename:
            source_type = request.form.get("source_type", "file")
            source_url = request.form.get("source_url")
            source_time = request.form.get("source_time")
            credibility = float(request.form.get("credibility", "1.0"))
            tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]

            for f in files:
                entry = MaterialManager.add_material(
                    project_id,
                    title=f.filename,
                    source_type=source_type,
                    source_url=source_url,
                    source_time=source_time,
                    credibility=credibility,
                    tags=tags,
                )
                # 保存原始文件
                saved_name = MaterialManager.save_raw_file(project_id, entry.material_id, f, f.filename)

                # 提取文本
                raw_path = MaterialManager._raw_dir(project_id) + "/" + saved_name
                try:
                    text = TextProcessor.extract_from_files([raw_path])
                except Exception:
                    text = ""
                ext_name = MaterialManager.save_extracted_text(project_id, entry.material_id, text)

                MaterialManager.update_material(
                    project_id,
                    entry.material_id,
                    saved_filename=saved_name,
                    extracted_text_path=ext_name,
                    text_length=len(text),
                )
                added.append(entry.material_id)

        # ── 手工文本模式 ──
        elif request.is_json:
            data = request.get_json(silent=True) or {}
            title = data.get("title", "手工输入")
            text = data.get("text", "")
            if not isinstance(text, str):
                text = str(text)
            if not text.strip():
                return jsonify({"success": False, "error": "text 不能为空"}), 400

            entry = MaterialManager.add_material(
                project_id,
                title=title,
                source_type=data.get("source_type", "manual"),
                source_url=data.get("source_url"),
                source_time=data.get("source_time"),
                credibility=float(data.get("credibility", 1.0)),
                tags=data.get("tags", []),
            )
            ext_name = MaterialManager.save_extracted_text(project_id, entry.material_id, text)
            MaterialManager.update_material(
                project_id,
                entry.material_id,
                extracted_text_path=ext_name,
                text_length=len(text),
            )
            added.append(entry.material_id)
        else:
            return jsonify({"success": False, "error": "请上传文件或提交 JSON 文本"}), 400

        # 更新项目级统计
        project.materials_count = MaterialManager.count(project_id)
        project.last_material_at = datetime.now().isoformat()
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "added_material_ids": added,
                "total_materials": project.materials_count,
            },
        })

    except Exception as e:
        logger.error(f"追加材料失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@incident_bp.route("/project/<project_id>/materials", methods=["GET"])
def list_materials(project_id: str):
    """返回项目材料时间线"""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        entries = MaterialManager.list_materials(project_id)
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "total": len(entries),
                "materials": [e.to_dict() for e in entries],
            },
        })
    except Exception as e:
        logger.error(f"获取材料列表失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/materials/<material_id>", methods=["GET"])
def get_material(project_id: str, material_id: str):
    """获取单条材料详情"""
    try:
        entry = MaterialManager.get_material(project_id, material_id)
        if not entry:
            return jsonify({"success": False, "error": "材料不存在"}), 404
        return jsonify({"success": True, "data": entry.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 基线管理
# ============================================================

@incident_bp.route("/project/<project_id>/baseline/rebuild", methods=["POST"])
def rebuild_baseline(project_id: str):
    """
    基于选定材料重建当前事实基线。
    如果请求中没有提供 confirmed_facts 等字段，则自动调用 LLM 分析材料文本。
    """
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        data = request.get_json(silent=True) or {}

        # 确定使用的材料
        material_ids = data.get("material_ids")
        if not material_ids:
            material_ids = [m.material_id for m in MaterialManager.list_materials(project_id)]

        # 判断是否需要 LLM 自动分析（前端没有传任何内容字段时）
        has_content = any(data.get(k) for k in [
            "confirmed_facts", "key_actors", "key_topics",
            "current_risks", "open_questions",
        ])

        if not has_content:
            # 用 LLM 自动分析材料文本
            combined_text = MaterialManager.get_combined_text(project_id, material_ids)
            if combined_text.strip():
                analysis = _llm_analyze_materials(combined_text, project.simulation_requirement)
            else:
                analysis = {}
        else:
            analysis = {}

        prev_baseline = BaselineManager.get_latest_baseline(project_id)

        snapshot = BaselineManager.create_baseline(
            project_id,
            based_on_material_ids=material_ids,
            previous_baseline_id=prev_baseline.baseline_id if prev_baseline else None,
            current_stage=data.get("current_stage") or analysis.get("current_stage"),
            confirmed_facts=data.get("confirmed_facts") or analysis.get("confirmed_facts", []),
            unconfirmed_claims=data.get("unconfirmed_claims") or analysis.get("unconfirmed_claims", []),
            key_actors=data.get("key_actors") or analysis.get("key_actors", []),
            key_topics=data.get("key_topics") or analysis.get("key_topics", []),
            open_questions=data.get("open_questions") or analysis.get("open_questions", []),
            current_risks=data.get("current_risks") or analysis.get("current_risks", []),
            recommended_monitoring_signals=data.get("recommended_monitoring_signals") or analysis.get("recommended_monitoring_signals", []),
            graph_id=project.graph_id,
        )

        # 更新项目当前基线
        project.current_baseline_id = snapshot.baseline_id
        ProjectManager.save_project(project)

        # ── 同步重建图谱（追加材料后图谱应更新） ──
        graph_task_id = None
        rebuild_graph = data.get("rebuild_graph", True)
        if rebuild_graph and project.ontology:
            try:
                # 1) 将所有材料文本合并写入 project 级 extracted_text
                all_text = MaterialManager.get_combined_text(project_id)
                if all_text.strip():
                    ProjectManager.save_extracted_text(project_id, all_text)

                    # 2) 启动异步图谱重建
                    from ..models.task import TaskManager, TaskStatus
                    from ..models.project import ProjectStatus
                    from ..services.graph_builder import GraphBuilderService
                    from ..config import Config
                    import threading

                    # 强制重置状态以允许重建
                    project.status = ProjectStatus.ONTOLOGY_GENERATED
                    project.error = None

                    task_manager = TaskManager()
                    graph_task_id = task_manager.create_task("重建基线-图谱更新")
                    project.graph_build_task_id = graph_task_id
                    project.status = ProjectStatus.GRAPH_BUILDING
                    ProjectManager.save_project(project)

                    def _rebuild_graph_task():
                        _logger = get_logger("nexusmind.incident.graph_rebuild")
                        try:
                            task_manager.update_task(graph_task_id, status=TaskStatus.PROCESSING, message="初始化图谱构建...", progress=5)
                            builder = GraphBuilderService()
                            chunks = TextProcessor.split_text(all_text, chunk_size=project.chunk_size or Config.DEFAULT_CHUNK_SIZE, overlap=project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)

                            task_manager.update_task(graph_task_id, message="创建图谱...", progress=10)
                            graph_id = builder.create_graph(name=project.name or "Incident Graph")
                            project.graph_id = graph_id
                            snapshot.graph_id = graph_id
                            BaselineManager.save_baseline(snapshot)
                            ProjectManager.save_project(project)

                            builder.set_ontology(graph_id, project.ontology)

                            def _prog(msg, ratio):
                                task_manager.update_task(graph_task_id, message=msg, progress=15 + int(ratio * 40))
                            task_manager.update_task(graph_task_id, message=f"添加 {len(chunks)} 个文本块...", progress=15)
                            episode_uuids = builder.add_text_batches(graph_id, chunks, batch_size=5, progress_callback=_prog)

                            def _wait_prog(msg, ratio):
                                task_manager.update_task(graph_task_id, message=msg, progress=55 + int(ratio * 35))
                            builder._wait_for_episodes(episode_uuids, _wait_prog)

                            task_manager.update_task(graph_task_id, message="标记图谱数据...", progress=92)
                            builder.tag_graph_data(graph_id)

                            try:
                                task_manager.update_task(graph_task_id, message="构建向量索引...", progress=93)
                                from ..services.vector_store import VectorStore
                                VectorStore().store_chunks(graph_id=graph_id, chunks=chunks)
                            except Exception as ve:
                                _logger.warning(f"向量索引构建失败（非致命）: {ve}")

                            project.status = ProjectStatus.GRAPH_COMPLETED
                            ProjectManager.save_project(project)
                            graph_data = builder.get_graph_data(graph_id)
                            task_manager.update_task(graph_task_id, status=TaskStatus.COMPLETED, message="图谱重建完成", progress=100, result={
                                "graph_id": graph_id,
                                "node_count": graph_data.get("node_count", 0),
                                "edge_count": graph_data.get("edge_count", 0),
                            })
                            _logger.info(f"图谱重建完成: {graph_id}")
                        except Exception as e:
                            _logger.error(f"图谱重建失败: {e}")
                            project.status = ProjectStatus.FAILED
                            project.error = str(e)
                            ProjectManager.save_project(project)
                            task_manager.update_task(graph_task_id, status=TaskStatus.FAILED, message=f"失败: {e}", error=str(e))

                    threading.Thread(target=_rebuild_graph_task, daemon=True).start()
                    logger.info(f"已启动图谱重建任务: {graph_task_id}")
            except Exception as ge:
                logger.warning(f"启动图谱重建失败（基线已保存）: {ge}")

        resp = snapshot.to_dict()
        if graph_task_id:
            resp["graph_task_id"] = graph_task_id

        return jsonify({
            "success": True,
            "data": resp,
        })

    except Exception as e:
        logger.error(f"重建基线失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


def _llm_analyze_materials(text: str, requirement: str = "") -> dict:
    """
    调用 LLM 自动从材料文本中提取基线结构化信息。
    返回 dict 包含 confirmed_facts, key_actors, key_topics, current_risks 等。
    """
    import json as _json
    try:
        from ..utils.llm_client import LLMClient
        llm = LLMClient()

        prompt = f"""请根据以下材料文本，提取结构化的事实基线信息。

【事件背景】
{requirement[:500] if requirement else '（无）'}

【材料原文】
{text[:4000]}

请严格按以下 JSON 格式输出（不要输出任何其他内容）：
{{
  "current_stage": "事件当前所处阶段（如：爆发期/发酵期/平台期/消退期）",
  "confirmed_facts": ["已确认的事实1", "已确认的事实2", ...],
  "unconfirmed_claims": ["未确认的说法1", ...],
  "key_actors": ["关键主体1", "关键主体2", ...],
  "key_topics": ["核心话题1", "核心话题2", ...],
  "open_questions": ["待解答的关键问题1", ...],
  "current_risks": ["当前主要风险1", ...],
  "recommended_monitoring_signals": ["建议监测信号1", ...]
}}"""

        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )

        # 提取 JSON
        resp_text = response.strip()
        if resp_text.startswith("```"):
            resp_text = resp_text.split("```")[1]
            if resp_text.startswith("json"):
                resp_text = resp_text[4:]
        result = _json.loads(resp_text)
        logger.info(f"LLM 基线分析完成: {len(result.get('confirmed_facts', []))} 条事实")
        return result

    except Exception as e:
        logger.warning(f"LLM 基线分析失败，使用空基线: {e}")
        return {}


@incident_bp.route("/project/<project_id>/baseline/current", methods=["GET"])
def get_current_baseline(project_id: str):
    """获取当前基线"""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        if not project.current_baseline_id:
            return jsonify({"success": True, "data": None, "message": "尚未创建基线"})

        snapshot = BaselineManager.get_baseline(project_id, project.current_baseline_id)
        return jsonify({
            "success": True,
            "data": snapshot.to_dict() if snapshot else None,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/baseline/history", methods=["GET"])
def list_baselines(project_id: str):
    """获取历史基线版本"""
    try:
        baselines = BaselineManager.list_baselines(project_id)
        return jsonify({
            "success": True,
            "data": {
                "total": len(baselines),
                "baselines": [b.to_dict() for b in baselines],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/baseline/diff", methods=["POST"])
def diff_baselines(project_id: str):
    """
    对比两个基线版本

    请求 JSON：
        {
            "baseline_a": "bl_xxx",
            "baseline_b": "bl_yyy"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        a_id = data.get("baseline_a")
        b_id = data.get("baseline_b")
        if not a_id or not b_id:
            return jsonify({"success": False, "error": "请提供 baseline_a 和 baseline_b"}), 400

        diff = BaselineManager.diff_baselines(project_id, a_id, b_id)
        if "error" in diff:
            return jsonify({"success": False, "error": diff["error"]}), 404
        return jsonify({"success": True, "data": diff})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/baseline/<baseline_id>", methods=["DELETE"])
def delete_baseline(project_id: str, baseline_id: str):
    """删除指定基线版本"""
    try:
        ok = BaselineManager.delete_baseline(project_id, baseline_id)
        if not ok:
            return jsonify({"success": False, "error": "基线不存在"}), 404
        # 如果删的是当前基线，切换到最新的
        project = ProjectManager.get_project(project_id)
        if project and getattr(project, "current_baseline_id", None) == baseline_id:
            latest = BaselineManager.get_latest_baseline(project_id)
            project.current_baseline_id = latest.baseline_id if latest else None
            ProjectManager.save_project(project)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 预测分支管理
# ============================================================

def _sync_forecast_run_status(run):
    if not run or not run.simulation_id:
        return run

    from ..services.simulation_manager import SimulationManager
    from ..services.simulation_runner import SimulationRunner

    manager = SimulationManager()
    sim_state = manager.get_simulation(run.simulation_id)
    runner_state = SimulationRunner.get_run_state(run.simulation_id)
    changed = False

    if runner_state and run.status == "running":
        runner_status = runner_state.runner_status.value if hasattr(runner_state.runner_status, "value") else str(runner_state.runner_status)
        if runner_status in ("completed", "stopped"):
            run.status = "completed"
            run.completed_at = run.completed_at or datetime.now().isoformat()
            changed = True
        elif runner_status == "failed":
            run.status = "failed"
            run.completed_at = run.completed_at or datetime.now().isoformat()
            run.error = runner_state.error
            changed = True

    if sim_state and run.status == "preparing":
        sim_status = sim_state.status.value if hasattr(sim_state.status, "value") else str(sim_state.status)
        if sim_status == "ready":
            run.status = "ready"
            changed = True
        elif sim_status == "failed":
            run.status = "failed"
            run.error = sim_state.error
            changed = True

    if changed:
        ForecastRunManager.save_run(run)

    return run

@incident_bp.route("/project/<project_id>/forecast/create", methods=["POST"])
def create_forecast_run(project_id: str):
    """
    创建预测分支

    请求 JSON：
        {
            "baseline_id": "bl_xxx",               // 必填
            "branch_type": "base",                  // 可选
            "branch_label": "基准预测",              // 可选
            "parent_run_id": "run_xxx",             // 可选（干预分支时指定父分支）
            "forecast_horizon_hours": 168,          // 可选
            "intervention_plan": {...}              // 可选（干预分支时的方案描述）
        }
    """
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        data = request.get_json(silent=True) or {}
        baseline_id = data.get("baseline_id")
        if not baseline_id:
            return jsonify({"success": False, "error": "请提供 baseline_id"}), 400

        baseline = BaselineManager.get_baseline(project_id, baseline_id)
        if not baseline:
            return jsonify({"success": False, "error": f"基线不存在: {baseline_id}"}), 404

        run = ForecastRunManager.create_run(
            project_id,
            baseline_id,
            branch_type=data.get("branch_type", "base"),
            branch_label=data.get("branch_label"),
            parent_run_id=data.get("parent_run_id"),
            forecast_horizon_hours=data.get("forecast_horizon_hours", 168),
            intervention_plan=data.get("intervention_plan"),
        )

        # 更新项目活跃分支
        project.active_run_id = run.run_id
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": run.to_dict(),
        })

    except Exception as e:
        logger.error(f"创建预测分支失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@incident_bp.route("/project/<project_id>/forecast/list", methods=["GET"])
def list_forecast_runs(project_id: str):
    """列出项目下所有预测分支"""
    try:
        runs = [_sync_forecast_run_status(r) for r in ForecastRunManager.list_runs(project_id)]
        return jsonify({
            "success": True,
            "data": {
                "total": len(runs),
                "runs": [r.to_dict() for r in runs],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/forecast/<run_id>", methods=["GET"])
def get_forecast_run(project_id: str, run_id: str):
    """获取单个预测分支详情"""
    try:
        run = ForecastRunManager.get_run(project_id, run_id)
        if not run:
            return jsonify({"success": False, "error": "预测分支不存在"}), 404
        run = _sync_forecast_run_status(run)
        return jsonify({"success": True, "data": run.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@incident_bp.route("/project/<project_id>/forecast/compare", methods=["POST"])
def compare_forecast_runs(project_id: str):
    """
    对比多个预测分支

    请求 JSON：
        {
            "run_ids": ["run_xxx", "run_yyy"]
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        run_ids = data.get("run_ids", [])
        if len(run_ids) < 2:
            return jsonify({"success": False, "error": "至少提供 2 个 run_id"}), 400

        result = ForecastRunManager.compare_runs(project_id, run_ids)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 自动引导
# ============================================================

@incident_bp.route("/project/<project_id>/bootstrap", methods=["POST"])
def bootstrap_project(project_id: str):
    """
    自动将项目已有的 extracted_text 导入为初始材料。
    仅在材料为空时执行，避免重复导入。
    """
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        # 已有材料则跳过
        if MaterialManager.count(project_id) > 0:
            return jsonify({"success": True, "data": {"message": "已有材料，跳过引导", "skipped": True}})

        text = ProjectManager.get_extracted_text(project_id) or ""
        if not text.strip():
            return jsonify({"success": False, "error": "项目无可用文本"}), 400

        title = (project.simulation_requirement or "种子材料")[:60]
        entry = MaterialManager.add_material(
            project_id,
            title=title,
            source_type="file",
        )
        ext_name = MaterialManager.save_extracted_text(project_id, entry.material_id, text)
        MaterialManager.update_material(
            project_id,
            entry.material_id,
            extracted_text_path=ext_name,
            text_length=len(text),
        )

        project.materials_count = MaterialManager.count(project_id)
        project.last_material_at = datetime.now().isoformat()
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "material_id": entry.material_id,
                "text_length": len(text),
                "message": "已从项目文本自动导入初始材料",
            },
        })

    except Exception as e:
        logger.error(f"自动引导失败: {e}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ============================================================
# 项目工作台概览
# ============================================================

@incident_bp.route("/project/<project_id>/overview", methods=["GET"])
def get_project_overview(project_id: str):
    """
    获取项目工作台概览（材料数、基线数、预测分支数等）
    """
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"项目不存在: {project_id}"}), 404

        materials = MaterialManager.list_materials(project_id)
        baselines = BaselineManager.list_baselines(project_id)
        runs = ForecastRunManager.list_runs(project_id)
        current_baseline = None
        if project.current_baseline_id:
            current_baseline = BaselineManager.get_baseline(project_id, project.current_baseline_id)

        return jsonify({
            "success": True,
            "data": {
                "project": project.to_dict(),
                "materials_count": len(materials),
                "baselines_count": len(baselines),
                "forecast_runs_count": len(runs),
                "current_baseline": current_baseline.to_dict() if current_baseline else None,
                "active_run_id": project.active_run_id,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
