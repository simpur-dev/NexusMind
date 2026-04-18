"""
NexusMind Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, g, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('nexusmind')
    
    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("NexusMind Backend 启动中...")
        logger.info("=" * 50)
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():

        path = request.path or ''
        is_simulation_status_polling = (
            request.method == 'GET'
            and path.startswith('/api/simulation/')
            and (path.endswith('/run-status') or path.endswith('/run-status/detail'))
        )

        g.skip_request_logging = is_simulation_status_polling
        if is_simulation_status_polling:
            return

        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):

        if getattr(g, 'skip_request_logging', False):
            return response
        logger.debug(f"响应: {response.status_code}")
        return response
    
    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # 健康检查
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'NexusMind Backend'}

    # 启动时接管孤儿模拟子进程（Flask debug autoreload / 崩溃后自恢复）
    # 仅在主进程执行，避免 Werkzeug reloader 的 stat 线程重复接管
    if should_log_startup and not app.config.get('TESTING', False):
        try:
            from .services.simulation_runner import SimulationRunner
            stats = SimulationRunner.reattach_running_simulations()
            if stats["scanned"] > 0:
                logger.info(
                    f"reattach 扫描 {stats['scanned']} 个 sim：接管 "
                    f"{stats['reattached']}，标记失败 {stats['marked_failed']}"
                )
        except Exception as e:
            logger.warning(f"reattach 启动扫描失败：{e}")

    if should_log_startup:
        logger.info("NexusMind Backend 启动完成")

    return app
