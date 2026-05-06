"""
NexusMind backend application factory.
"""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, g, request
from flask_cors import CORS

from .config import Config
from .utils.logger import get_logger, setup_logger

_STATUS_POLLING_SUFFIXES = ('/run-status', '/run-status/detail')


def _enable_unicode_json(app: Flask) -> None:
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False


def _should_emit_startup_log(app: Flask) -> bool:
    debug_mode = app.config.get('DEBUG', False)
    reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    return (not debug_mode) or reloader_child


def _is_simulation_status_polling() -> bool:
    path = request.path or ''
    return (
        request.method == 'GET'
        and path.startswith('/api/simulation/')
        and path.endswith(_STATUS_POLLING_SUFFIXES)
    )


def _install_request_logging(app: Flask, logger) -> None:
    @app.before_request
    def capture_request_log():
        g.skip_request_logging = _is_simulation_status_polling()
        if g.skip_request_logging:
            return
        logger.debug(f"request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"request_body: {request.get_json(silent=True)}")

    @app.after_request
    def capture_response_log(response):
        if not getattr(g, 'skip_request_logging', False):
            logger.debug(f"response: {response.status_code}")
        return response


def _register_blueprints(app: Flask) -> None:
    from .api import evaluation_bp, forecast_bp, graph_bp, incident_bp, report_bp, simulation_bp

    for blueprint, prefix in (
        (graph_bp, '/api/graph'),
        (simulation_bp, '/api/simulation'),
        (report_bp, '/api/report'),
        (evaluation_bp, '/api/evaluation'),
        (incident_bp, '/api/incident'),
        (forecast_bp, '/api/forecast'),
    ):
        app.register_blueprint(blueprint, url_prefix=prefix)


def _register_health_check(app: Flask) -> None:
    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'NexusMind Backend'}


def _install_simulation_shutdown_hook(logger, should_log_startup: bool) -> None:
    from .services.simulation_runner import SimulationRunner

    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("registered simulation process cleanup hook")


def _reattach_running_simulations(app: Flask, logger, should_log_startup: bool) -> None:
    if not should_log_startup or app.config.get('TESTING', False):
        return
    try:
        from .services.simulation_runner import SimulationRunner
        stats = SimulationRunner.reattach_running_simulations()
        if stats["scanned"] > 0:
            logger.info(
                f"reattach scanned {stats['scanned']} simulations: "
                f"reattached {stats['reattached']}, marked_failed {stats['marked_failed']}"
            )
    except Exception as exc:
        logger.warning(f"reattach startup scan failed: {exc}")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _enable_unicode_json(app)

    logger = setup_logger('nexusmind')
    get_logger('nexusmind.api')
    should_log_startup = _should_emit_startup_log(app)

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("NexusMind Backend starting...")
        logger.info("=" * 50)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    _install_simulation_shutdown_hook(logger, should_log_startup)
    _install_request_logging(app, logger)
    _register_blueprints(app)
    _register_health_check(app)
    _reattach_running_simulations(app, logger, should_log_startup)

    if should_log_startup:
        logger.info("NexusMind Backend started")
    return app
