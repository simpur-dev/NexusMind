"""
Report API routes for report generation, retrieval, chat, logs, and debug tools.
"""

import os
import tempfile
import threading
import traceback
import uuid
from pathlib import Path

from flask import request, jsonify, send_file

from . import report_bp
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger

logger = get_logger('nexusmind.api.report')


def _json_body():
    return request.get_json(silent=True) or {}


def _ok(data=None, **extra):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def _fail(message, status=400, trace=False, **extra):
    payload = {"success": False, "error": message}
    if trace:
        payload["traceback"] = traceback.format_exc()
    payload.update(extra)
    return jsonify(payload), status


def _fatal(context, exc, trace=True):
    logger.error(f"{context}: {str(exc)}")
    return _fail(str(exc), 500, trace=trace)


def _missing(message):
    return _fail(message, 400)


def _not_found(message, **extra):
    return _fail(message, 404, **extra)


def _report_status_value(report):
    return report.status.value if report else None


def _report_is_complete(report):
    return bool(report and report.status == ReportStatus.COMPLETED)


def _get_state(simulation_id):
    return SimulationManager().get_simulation(simulation_id)


def _get_project_for_state(state):
    return ProjectManager.get_project(state.project_id) if state else None


def _resolve_graph_id(state, project):
    return (state.graph_id if state else None) or (project.graph_id if project else None)


def _completed_report_payload(simulation_id, report, message="Report generated"):
    return {
        "simulation_id": simulation_id,
        "report_id": report.report_id,
        "status": "completed",
        "progress": 100,
        "message": message,
        "already_completed": True,
    }


def _build_baseline_context(project_id, baseline_id):
    if not baseline_id:
        return ""
    try:
        from ..models.baseline import BaselineManager
        baseline = BaselineManager.get_baseline(project_id, baseline_id)
        if not baseline:
            return ""
        parts = [f"\n\n[Current baseline analysis: {baseline.current_stage or 'unknown'}]"]
        if baseline.confirmed_facts:
            parts.append(f"Confirmed facts: {'; '.join(baseline.confirmed_facts[:8])}")
        if baseline.current_risks:
            parts.append(f"Current risks: {'; '.join(baseline.current_risks[:8])}")
        if baseline.key_actors:
            parts.append(f"Key actors: {', '.join(baseline.key_actors[:6])}")
        if baseline.key_topics:
            parts.append(f"Key topics: {', '.join(baseline.key_topics[:6])}")
        parts.append(f"Event stage: {baseline.current_stage or 'unknown'}")
        logger.info(f"Baseline context loaded: baseline_id={baseline_id}, stage={baseline.current_stage}")
        return "\n".join(parts)
    except Exception as exc:
        logger.warning(f"Failed to load baseline {baseline_id}: {exc}")
        return ""


def _create_report_task(simulation_id, graph_id, report_id, baseline_id):
    task_manager = TaskManager()
    task_id = task_manager.create_task(
        task_type="report_generate",
        metadata={
            "simulation_id": simulation_id,
            "graph_id": graph_id,
            "report_id": report_id,
            "baseline_id": baseline_id or "",
        },
    )
    return task_manager, task_id


def _persist_project_report_id(project_id, report_id):
    try:
        project = ProjectManager.get_project(project_id)
        if project:
            project.report_id = report_id
            ProjectManager.save_project(project)
            logger.info(f"Saved report_id={report_id} back to project {project_id}")
    except Exception as exc:
        logger.warning(f"Failed to persist report_id to project: {exc}")


def _run_report_generation(task_manager, task_id, graph_id, simulation_id, project_id, requirement, report_id):
    try:
        task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=0,
            message="Initializing Report Agent...",
        )
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=requirement,
        )

        def progress_callback(stage, progress, message):
            task_manager.update_task(task_id, progress=progress, message=f"[{stage}] {message}")

        report = agent.generate_report(progress_callback=progress_callback, report_id=report_id)
        ReportManager.save_report(report)
        if report.status == ReportStatus.COMPLETED:
            _persist_project_report_id(project_id, report.report_id)
            task_manager.complete_task(task_id, {
                "report_id": report.report_id,
                "simulation_id": simulation_id,
                "status": "completed",
            })
        else:
            task_manager.fail_task(task_id, report.error or "Report generation failed")
    except Exception as exc:
        logger.error(f"Report generation failed: {str(exc)}")
        task_manager.fail_task(task_id, str(exc))


def _launch_report_thread(*args):
    thread = threading.Thread(target=_run_report_generation, args=args, daemon=True)
    thread.start()


def _simulation_context(simulation_id):
    state = _get_state(simulation_id)
    if not state:
        return None, None, None, _not_found(f"Simulation not found: {simulation_id}")
    project = _get_project_for_state(state)
    if not project:
        return state, None, None, _not_found(f"Project not found: {state.project_id}")
    graph_id = _resolve_graph_id(state, project)
    return state, project, graph_id, None


def _send_markdown_file(report_id, report):
    markdown_path = ReportManager._get_report_markdown_path(report_id)
    if os.path.exists(markdown_path):
        return send_file(markdown_path, as_attachment=True, download_name=f"{report_id}.md")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as file:
        file.write(report.markdown_content)
        temp_path = file.name
    return send_file(temp_path, as_attachment=True, download_name=f"{report_id}.md")


def _section_payload(report_id, sections):
    report = ReportManager.get_report(report_id)
    return {
        "report_id": report_id,
        "sections": sections,
        "total_sections": len(sections),
        "is_complete": _report_is_complete(report),
    }


def _stream_payload(logs):
    return {"logs": logs, "count": len(logs)}


@report_bp.route('/generate', methods=['POST'])
def generate_report():
    """Start asynchronous report generation."""
    try:
        data = _json_body()
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return _missing("simulation_id is required")

        if not data.get('force_regenerate', False):
            existing = ReportManager.get_report_by_simulation(simulation_id)
            if _report_is_complete(existing):
                return _ok({
                    "simulation_id": simulation_id,
                    "report_id": existing.report_id,
                    "status": "completed",
                    "message": "Report already exists",
                    "already_generated": True,
                })

        state, project, graph_id, error = _simulation_context(simulation_id)
        if error:
            return error
        if not graph_id:
            return _missing("graph_id is missing; build the graph first")
        if not project.simulation_requirement:
            return _missing("simulation requirement is missing")

        baseline_id = data.get('baseline_id')
        requirement = project.simulation_requirement + _build_baseline_context(state.project_id, baseline_id)
        report_id = f"report_{uuid.uuid4().hex[:12]}"
        task_manager, task_id = _create_report_task(simulation_id, graph_id, report_id, baseline_id)
        _launch_report_thread(task_manager, task_id, graph_id, simulation_id, state.project_id, requirement, report_id)
        return _ok({
            "simulation_id": simulation_id,
            "report_id": report_id,
            "task_id": task_id,
            "status": "generating",
            "message": "Report generation task started; poll /api/report/generate/status for progress",
            "already_generated": False,
        })
    except Exception as exc:
        return _fatal("Failed to start report generation", exc)


@report_bp.route('/generate/status', methods=['POST'])
def get_generate_status():
    """Return report generation task progress."""
    try:
        data = _json_body()
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        if simulation_id:
            existing = ReportManager.get_report_by_simulation(simulation_id)
            if _report_is_complete(existing):
                return _ok(_completed_report_payload(simulation_id, existing))
        if not task_id:
            return _missing("task_id or simulation_id is required")
        task = TaskManager().get_task(task_id)
        if not task:
            return _not_found(f"Task not found: {task_id}")
        return _ok(task.to_dict())
    except Exception as exc:
        return _fatal("Failed to query report task status", exc, trace=False)


@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """Return report details."""
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return _not_found(f"Report not found: {report_id}")
        return _ok(report.to_dict())
    except Exception as exc:
        return _fatal("Failed to get report", exc)


@report_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
def get_report_by_simulation(simulation_id: str):
    """Return the report for a simulation."""
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        if not report:
            return _not_found(f"No report for simulation: {simulation_id}", has_report=False)
        return _ok(report.to_dict(), has_report=True)
    except Exception as exc:
        return _fatal("Failed to get report", exc)


@report_bp.route('/list', methods=['GET'])
def list_reports():
    """List reports."""
    try:
        reports = ReportManager.list_reports(
            simulation_id=request.args.get('simulation_id'),
            limit=request.args.get('limit', 50, type=int),
        )
        return _ok([report.to_dict() for report in reports], count=len(reports))
    except Exception as exc:
        return _fatal("Failed to list reports", exc)


@report_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """Download report markdown."""
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return _not_found(f"Report not found: {report_id}")
        return _send_markdown_file(report_id, report)
    except Exception as exc:
        return _fatal("Failed to download report", exc)


@report_bp.route('/<report_id>', methods=['DELETE'])
def delete_report(report_id: str):
    """Delete a report."""
    try:
        if not ReportManager.delete_report(report_id):
            return _not_found(f"Report not found: {report_id}")
        return _ok(message=f"Report deleted: {report_id}")
    except Exception as exc:
        return _fatal("Failed to delete report", exc)


@report_bp.route('/chat', methods=['POST'])
def chat_with_report_agent():
    """Chat with Report Agent."""
    try:
        data = _json_body()
        simulation_id = data.get('simulation_id')
        message = data.get('message')
        if not simulation_id:
            return _missing("simulation_id is required")
        if not message:
            return _missing("message is required")
        state, project, graph_id, error = _simulation_context(simulation_id)
        if error:
            return error
        if not graph_id:
            return _missing("graph_id is missing")
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=project.simulation_requirement or "",
        )
        return _ok(agent.chat(message=message, chat_history=data.get('chat_history', [])))
    except Exception as exc:
        return _fatal("Chat failed", exc)


@report_bp.route('/<report_id>/progress', methods=['GET'])
def get_report_progress(report_id: str):
    """Return live report progress."""
    try:
        progress = ReportManager.get_progress(report_id)
        if not progress:
            return _not_found(f"Report progress unavailable: {report_id}")
        return _ok(progress)
    except Exception as exc:
        return _fatal("Failed to get report progress", exc)


@report_bp.route('/<report_id>/sections', methods=['GET'])
def get_report_sections(report_id: str):
    """Return generated report sections."""
    try:
        sections = ReportManager.get_generated_sections(report_id)
        return _ok(_section_payload(report_id, sections))
    except Exception as exc:
        return _fatal("Failed to get report sections", exc)


@report_bp.route('/<report_id>/section/<int:section_index>', methods=['GET'])
def get_single_section(report_id: str, section_index: int):
    """Return one generated report section."""
    try:
        section_path = Path(ReportManager._get_section_path(report_id, section_index))
        if not section_path.exists():
            return _not_found(f"Section not found: section_{section_index:02d}.md")
        return _ok({
            "filename": f"section_{section_index:02d}.md",
            "section_index": section_index,
            "content": section_path.read_text(encoding='utf-8'),
        })
    except Exception as exc:
        return _fatal("Failed to get report section", exc)


@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """Check whether a simulation has a completed report."""
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        return _ok({
            "simulation_id": simulation_id,
            "has_report": report is not None,
            "report_status": _report_status_value(report),
            "report_id": report.report_id if report else None,
            "interview_unlocked": _report_is_complete(report),
        })
    except Exception as exc:
        return _fatal("Failed to check report status", exc)


@report_bp.route('/<report_id>/agent-log', methods=['GET'])
def get_agent_log(report_id: str):
    """Return structured Report Agent log lines."""
    try:
        return _ok(ReportManager.get_agent_log(report_id, from_line=request.args.get('from_line', 0, type=int)))
    except Exception as exc:
        return _fatal("Failed to get agent log", exc)


@report_bp.route('/<report_id>/agent-log/stream', methods=['GET'])
def stream_agent_log(report_id: str):
    """Return full structured Report Agent log."""
    try:
        return _ok(_stream_payload(ReportManager.get_agent_log_stream(report_id)))
    except Exception as exc:
        return _fatal("Failed to get agent log", exc)


@report_bp.route('/<report_id>/console-log', methods=['GET'])
def get_console_log(report_id: str):
    """Return console log lines."""
    try:
        return _ok(ReportManager.get_console_log(report_id, from_line=request.args.get('from_line', 0, type=int)))
    except Exception as exc:
        return _fatal("Failed to get console log", exc)


@report_bp.route('/<report_id>/console-log/stream', methods=['GET'])
def stream_console_log(report_id: str):
    """Return full console log."""
    try:
        return _ok(_stream_payload(ReportManager.get_console_log_stream(report_id)))
    except Exception as exc:
        return _fatal("Failed to get console log", exc)


@report_bp.route('/tools/search', methods=['POST'])
def search_graph_tool():
    """Debug graph search tool endpoint."""
    try:
        data = _json_body()
        graph_id = data.get('graph_id')
        query = data.get('query')
        if not graph_id or not query:
            return _missing("graph_id and query are required")
        from ..services.graph_tools import GraphToolsService
        result = GraphToolsService().search_graph(graph_id=graph_id, query=query, limit=data.get('limit', 10))
        return _ok(result.to_dict())
    except Exception as exc:
        return _fatal("Graph search failed", exc)


@report_bp.route('/tools/statistics', methods=['POST'])
def get_graph_statistics_tool():
    """Debug graph statistics endpoint."""
    try:
        data = _json_body()
        graph_id = data.get('graph_id')
        if not graph_id:
            return _missing("graph_id is required")
        from ..services.graph_tools import GraphToolsService
        return _ok(GraphToolsService().get_graph_statistics(graph_id))
    except Exception as exc:
        return _fatal("Failed to get graph statistics", exc)
