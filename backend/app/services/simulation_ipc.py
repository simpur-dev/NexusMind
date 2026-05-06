"""
File-system IPC bridge between the Flask backend and simulation workers.
"""

import ctypes
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..utils.logger import get_logger

logger = get_logger('nexusmind.simulation_ipc')

COMMANDS_DIRNAME = "ipc_commands"
RESPONSES_DIRNAME = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"
ENV_STALE_SECONDS = 300
ALIVE_CHECK_INTERVAL = 15


class CommandType(str, Enum):
    """IPC command types."""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    INJECT_EVENT = "inject_event"
    CLOSE_ENV = "close_env"


class CommandStatus(str, Enum):
    """IPC command status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IPCCommand:
    """Serialized IPC command."""
    command_id: str
    command_type: CommandType
    args: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "args": self.args,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCCommand':
        return cls(
            command_id=data["command_id"],
            command_type=CommandType(data["command_type"]),
            args=data.get("args", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class IPCResponse:
    """Serialized IPC response."""
    command_id: str
    status: CommandStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCResponse':
        return cls(
            command_id=data["command_id"],
            status=CommandStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp_path.replace(path)


def _delete_quietly(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass


def _pid_is_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return True
    if pid_int <= 0:
        return False
    if os.name == 'nt':
        process_query = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(process_query, False, pid_int)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            return bool(ok) and exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid_int, 0)
        return True
    except OSError:
        return False


def _make_command(command_type: CommandType, args: Dict[str, Any]) -> IPCCommand:
    return IPCCommand(command_id=str(uuid.uuid4()), command_type=command_type, args=args)


class _IPCPaths:
    def __init__(self, simulation_dir: str):
        self.root = Path(simulation_dir)
        self.commands = self.root / COMMANDS_DIRNAME
        self.responses = self.root / RESPONSES_DIRNAME
        self.env_status = self.root / ENV_STATUS_FILE
        _ensure_dir(self.commands)
        _ensure_dir(self.responses)

    def command_file(self, command_id: str) -> Path:
        return self.commands / f"{command_id}.json"

    def response_file(self, command_id: str) -> Path:
        return self.responses / f"{command_id}.json"


class SimulationIPCClient:
    """IPC client used by Flask routes to command a running simulation."""

    def __init__(self, simulation_dir: str):
        self.simulation_dir = simulation_dir
        self._paths = _IPCPaths(simulation_dir)
        self.commands_dir = str(self._paths.commands)
        self.responses_dir = str(self._paths.responses)

    def send_command(
        self,
        command_type: CommandType,
        args: Dict[str, Any],
        timeout: float = 60.0,
        poll_interval: float = 0.5
    ) -> IPCResponse:
        command = _make_command(command_type, args)
        command_file = self._paths.command_file(command.command_id)
        response_file = self._paths.response_file(command.command_id)
        _write_json(command_file, command.to_dict())
        logger.info(f"IPC command sent: {command_type.value}, command_id={command.command_id}")

        start_time = time.time()
        next_alive_check = start_time + ALIVE_CHECK_INTERVAL
        while time.time() - start_time < timeout:
            response = self._try_read_response(response_file)
            if response:
                _delete_quietly(command_file, response_file)
                logger.info(f"IPC response received: command_id={command.command_id}, status={response.status.value}")
                return response

            now = time.time()
            if now >= next_alive_check:
                next_alive_check = now + ALIVE_CHECK_INTERVAL
                if not self.check_env_alive():
                    _delete_quietly(command_file)
                    logger.warning(f"Simulation process exited while waiting for IPC response: command_id={command.command_id}")
                    raise TimeoutError(f"Simulation process exited before command completed ({command_type.value})")

            time.sleep(poll_interval)

        _delete_quietly(command_file)
        logger.error(f"IPC response timeout: command_id={command.command_id}")
        raise TimeoutError(f"Command response timed out after {timeout} seconds")

    def _try_read_response(self, response_file: Path) -> Optional[IPCResponse]:
        if not response_file.exists():
            return None
        try:
            return IPCResponse.from_dict(_read_json(response_file))
        except (json.JSONDecodeError, KeyError, OSError, ValueError) as exc:
            logger.warning(f"Failed to parse IPC response: {exc}")
            return None

    def send_interview(
        self,
        agent_id: int,
        prompt: str,
        platform: str = None,
        timeout: float = 60.0
    ) -> IPCResponse:
        args = {"agent_id": agent_id, "prompt": prompt}
        if platform:
            args["platform"] = platform
        return self.send_command(CommandType.INTERVIEW, args, timeout=timeout)

    def send_batch_interview(
        self,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> IPCResponse:
        args = {"interviews": interviews}
        if platform:
            args["platform"] = platform
        return self.send_command(CommandType.BATCH_INTERVIEW, args, timeout=timeout)

    def send_inject_event(
        self,
        event_type: str,
        description: str,
        severity: float = 0.7,
        affected_variables: Dict[str, float] = None,
        timeout: float = 10.0
    ) -> IPCResponse:
        args = {
            "event_type": event_type,
            "description": description,
            "severity": max(0.0, min(1.0, severity)),
        }
        if affected_variables:
            args["affected_variables"] = affected_variables
        return self.send_command(CommandType.INJECT_EVENT, args, timeout=timeout)

    def send_close_env(self, timeout: float = 30.0) -> IPCResponse:
        return self.send_command(CommandType.CLOSE_ENV, {}, timeout=timeout)

    def check_env_alive(self) -> bool:
        status_file = self._paths.env_status
        if not status_file.exists():
            return False
        try:
            status = _read_json(status_file)
        except (json.JSONDecodeError, OSError):
            return False
        if status.get("status") != "alive":
            return False
        if status.get("pid") and not _pid_is_alive(status.get("pid")):
            logger.warning(f"env_status says alive but PID {status.get('pid')} is gone")
            return False
        if time.time() - status_file.stat().st_mtime > ENV_STALE_SECONDS:
            logger.warning("env_status.json is stale; treating simulation as not alive")
            return False
        return True


class SimulationIPCServer:
    """IPC server used by simulation scripts to poll commands and publish responses."""

    def __init__(self, simulation_dir: str):
        self.simulation_dir = simulation_dir
        self._paths = _IPCPaths(simulation_dir)
        self.commands_dir = str(self._paths.commands)
        self.responses_dir = str(self._paths.responses)
        self._running = False

    def start(self):
        self._running = True
        self._update_env_status("alive")

    def stop(self):
        self._running = False
        self._update_env_status("stopped")

    def _update_env_status(self, status: str):
        _write_json(self._paths.env_status, {
            "status": status,
            "pid": os.getpid(),
            "timestamp": datetime.now().isoformat(),
        })

    def poll_commands(self) -> Optional[IPCCommand]:
        if not self._paths.commands.exists():
            return None
        command_files = sorted(
            self._paths.commands.glob('*.json'),
            key=lambda path: path.stat().st_mtime,
        )
        for command_file in command_files:
            try:
                return IPCCommand.from_dict(_read_json(command_file))
            except (json.JSONDecodeError, KeyError, OSError, ValueError) as exc:
                logger.warning(f"Failed to read IPC command file: {command_file}, {exc}")
        return None

    def send_response(self, response: IPCResponse):
        _write_json(self._paths.response_file(response.command_id), response.to_dict())
        _delete_quietly(self._paths.command_file(response.command_id))

    def send_success(self, command_id: str, result: Dict[str, Any]):
        self.send_response(IPCResponse(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            result=result,
        ))

    def send_error(self, command_id: str, error: str):
        self.send_response(IPCResponse(
            command_id=command_id,
            status=CommandStatus.FAILED,
            error=error,
        ))
