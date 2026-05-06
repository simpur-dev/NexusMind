"""
动作日志记录器
用于记录OASIS模拟中每个Agent的动作，供后端监控使用

日志结构:
    sim_xxx/
    ├── twitter/
    │   └── actions.jsonl    # Twitter 平台动作日志
    ├── reddit/
    │   └── actions.jsonl    # Reddit 平台动作日志
    ├── simulation.log       # 主模拟进程日志
    └── run_state.json       # 运行状态（API 查询用）
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def _timestamp() -> str:
    return datetime.now().isoformat()


def _write_json_line(path, payload: Dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def _action_payload(
    round_num: int,
    agent_id: int,
    agent_name: str,
    action_type: str,
    action_args: Optional[Dict[str, Any]] = None,
    result: Optional[str] = None,
    success: bool = True,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "round": round_num,
        "timestamp": _timestamp(),
        "agent_id": agent_id,
        "agent_name": agent_name,
        "action_type": action_type,
        "action_args": action_args or {},
        "result": result,
        "success": success,
    }
    if platform:
        payload["platform"] = platform
    return payload


class PlatformActionLogger:
    """单平台动作日志记录器"""

    def __init__(self, platform: str, base_dir: str):
        """
        初始化日志记录器

        Args:
            platform: 平台名称 (twitter/reddit)
            base_dir: 模拟目录的基础路径
        """
        self.platform = platform
        self.base_dir = base_dir
        self.log_dir = str(Path(base_dir) / platform)
        self.log_path = str(Path(self.log_dir) / "actions.jsonl")
        self._ensure_dir()

    def _ensure_dir(self):
        """确保目录存在"""
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def _append(self, payload: Dict[str, Any]):
        _write_json_line(self.log_path, payload)

    def log_action(
        self,
        round_num: int,
        agent_id: int,
        agent_name: str,
        action_type: str,
        action_args: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        success: bool = True
    ):
        """记录一个动作"""
        self._append(_action_payload(
            round_num=round_num,
            agent_id=agent_id,
            agent_name=agent_name,
            action_type=action_type,
            action_args=action_args,
            result=result,
            success=success,
        ))

    def log_round_start(self, round_num: int, simulated_hour: int):
        """记录轮次开始"""
        self._append({
            "round": round_num,
            "timestamp": _timestamp(),
            "event_type": "round_start",
            "simulated_hour": simulated_hour,
        })

    def log_round_end(self, round_num: int, actions_count: int):
        """记录轮次结束"""
        self._append({
            "round": round_num,
            "timestamp": _timestamp(),
            "event_type": "round_end",
            "actions_count": actions_count,
        })

    def log_simulation_start(self, config: Dict[str, Any]):
        """记录模拟开始"""
        self._append({
            "timestamp": _timestamp(),
            "event_type": "simulation_start",
            "platform": self.platform,
            "total_rounds": config.get("time_config", {}).get("total_simulation_hours", 72) * 2,
            "agents_count": len(config.get("agent_configs", [])),
        })

    def log_simulation_end(self, total_rounds: int, total_actions: int):
        """记录模拟结束"""
        self._append({
            "timestamp": _timestamp(),
            "event_type": "simulation_end",
            "platform": self.platform,
            "total_rounds": total_rounds,
            "total_actions": total_actions,
        })


class SimulationLogManager:
    """
    模拟日志管理器
    统一管理所有日志文件，按平台分离
    """

    def __init__(self, simulation_dir: str):
        """
        初始化日志管理器

        Args:
            simulation_dir: 模拟目录路径
        """
        self.simulation_dir = simulation_dir
        self.twitter_logger: Optional[PlatformActionLogger] = None
        self.reddit_logger: Optional[PlatformActionLogger] = None
        self._main_logger: Optional[logging.Logger] = None
        self._setup_main_logger()

    def _setup_main_logger(self):
        """设置主模拟日志"""
        Path(self.simulation_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(self.simulation_dir) / "simulation.log"
        logger_name = f"simulation.{Path(self.simulation_dir).name}"
        self._main_logger = logging.getLogger(logger_name)
        self._main_logger.setLevel(logging.INFO)
        self._main_logger.handlers.clear()
        self._main_logger.propagate = False

        file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        ))

        self._main_logger.addHandler(file_handler)
        self._main_logger.addHandler(console_handler)

    def _get_platform_logger(self, platform: str) -> PlatformActionLogger:
        attr = f"{platform}_logger"
        logger = getattr(self, attr)
        if logger is None:
            logger = PlatformActionLogger(platform, self.simulation_dir)
            setattr(self, attr, logger)
        return logger

    def get_twitter_logger(self) -> PlatformActionLogger:
        """获取 Twitter 平台日志记录器"""
        return self._get_platform_logger("twitter")

    def get_reddit_logger(self) -> PlatformActionLogger:
        """获取 Reddit 平台日志记录器"""
        return self._get_platform_logger("reddit")

    def log(self, message: str, level: str = "info"):
        """记录主日志"""
        if self._main_logger:
            log_func = getattr(self._main_logger, level.lower(), self._main_logger.info)
            log_func(message)

    def info(self, message: str):
        self.log(message, "info")

    def warning(self, message: str):
        self.log(message, "warning")

    def error(self, message: str):
        self.log(message, "error")

    def debug(self, message: str):
        self.log(message, "debug")


class ActionLogger:
    """
    动作日志记录器（兼容旧接口）
    建议使用 SimulationLogManager 代替
    """

    def __init__(self, log_path: str):
        self.log_path = log_path
        self._ensure_dir()

    def _ensure_dir(self):
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def _append(self, payload: Dict[str, Any]):
        _write_json_line(self.log_path, payload)

    def log_action(
        self,
        round_num: int,
        platform: str,
        agent_id: int,
        agent_name: str,
        action_type: str,
        action_args: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        success: bool = True
    ):
        self._append(_action_payload(
            round_num=round_num,
            agent_id=agent_id,
            agent_name=agent_name,
            action_type=action_type,
            action_args=action_args,
            result=result,
            success=success,
            platform=platform,
        ))

    def log_round_start(self, round_num: int, simulated_hour: int, platform: str):
        self._append({
            "round": round_num,
            "timestamp": _timestamp(),
            "platform": platform,
            "event_type": "round_start",
            "simulated_hour": simulated_hour,
        })

    def log_round_end(self, round_num: int, actions_count: int, platform: str):
        self._append({
            "round": round_num,
            "timestamp": _timestamp(),
            "platform": platform,
            "event_type": "round_end",
            "actions_count": actions_count,
        })

    def log_simulation_start(self, platform: str, config: Dict[str, Any]):
        self._append({
            "timestamp": _timestamp(),
            "platform": platform,
            "event_type": "simulation_start",
            "total_rounds": config.get("time_config", {}).get("total_simulation_hours", 72) * 2,
            "agents_count": len(config.get("agent_configs", [])),
        })

    def log_simulation_end(self, platform: str, total_rounds: int, total_actions: int):
        self._append({
            "timestamp": _timestamp(),
            "platform": platform,
            "event_type": "simulation_end",
            "total_rounds": total_rounds,
            "total_actions": total_actions,
        })


_global_logger: Optional[ActionLogger] = None


def get_logger(log_path: Optional[str] = None) -> ActionLogger:
    """获取全局日志实例（兼容旧接口）"""
    global _global_logger

    if log_path or _global_logger is None:
        _global_logger = ActionLogger(log_path or "actions.jsonl")

    return _global_logger
