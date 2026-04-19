"""
OASIS模拟管理器
管理Twitter和Reddit双平台并行模拟
使用预设脚本 + LLM智能生成配置参数
"""

import os
import sys
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .entity_reader import EntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters

logger = get_logger('nexusmind.simulation')


class SimulationStatus(str, Enum):
    """模拟状态"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # 模拟被手动停止
    COMPLETED = "completed"  # 模拟自然完成
    FAILED = "failed"


class PlatformType(str, Enum):
    """平台类型"""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """模拟状态"""
    simulation_id: str
    project_id: str
    graph_id: str
    
    # 平台启用状态
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # 状态
    status: SimulationStatus = SimulationStatus.CREATED
    
    # 准备阶段数据
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # 配置生成信息
    config_generated: bool = False
    config_reasoning: str = ""
    
    # 运行时数据
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 错误信息
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """完整状态字典（内部使用）"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """简化状态字典（API返回使用）"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """
    模拟管理器
    
    核心功能：
    1. 从图谱读取实体并过滤
    2. 生成OASIS Agent Profile
    3. 使用LLM智能生成模拟配置参数
    4. 准备预设脚本所需的所有文件
    """
    
    # 模拟数据存储目录
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__), 
        '../../uploads/simulations'
    )
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        
        # 内存中的模拟状态缓存
        self._simulations: Dict[str, SimulationState] = {}
    
    def _get_simulation_dir(self, simulation_id: str, create: bool = False) -> str:
        """获取模拟数据目录。

        注意：默认 create=False，不会自动创建目录。这避免了在删除模拟时，
        任何意外调用 `_get_simulation_dir` 的代码路径重新创建空目录的问题。
        仅当明确需要写入时（如 `_save_simulation_state`）才设 create=True。
        """
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        if create:
            os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """保存模拟状态到文件"""
        sim_dir = self._get_simulation_dir(state.simulation_id, create=True)
        state_file = os.path.join(sim_dir, "state.json")
        
        state.updated_at = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """从文件加载模拟状态"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )
        
        self._simulations[simulation_id] = state
        return state
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """
        创建新的模拟（同一项目复用已有模拟，避免重复生成Agent人设）
        
        Args:
            project_id: 项目ID
            graph_id: 图谱ID
            enable_twitter: 是否启用Twitter模拟
            enable_reddit: 是否启用Reddit模拟
            
        Returns:
            SimulationState
        """
        # 检查该项目是否已有模拟，如果有则复用
        existing = self._find_simulation_by_project(project_id)
        if existing:
            logger.info(f"复用已有模拟: {existing.simulation_id}, project={project_id}")
            return existing
        
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"创建模拟: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def _find_simulation_by_project(self, project_id: str) -> Optional[SimulationState]:
        """查找项目对应的已有模拟"""
        import os
        sim_base = Config.OASIS_SIMULATION_DATA_DIR
        if not os.path.exists(sim_base):
            return None
        
        for sim_dir_name in os.listdir(sim_base):
            if not sim_dir_name.startswith("sim_"):
                continue
            state_file = os.path.join(sim_base, sim_dir_name, "state.json")
            if not os.path.exists(state_file):
                continue
            try:
                import json
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("project_id") == project_id:
                    return self._load_simulation_state(sim_dir_name)
            except Exception:
                continue
        return None
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 8,
        resume: bool = False
    ) -> SimulationState:
        """
        准备模拟环境（全程自动化）
        
        步骤：
        1. 从图谱读取并过滤实体
        2. 为每个实体生成OASIS Agent Profile（可选LLM增强，支持并行）
        3. 使用LLM智能生成模拟配置参数（时间、活跃度、发言频率等）
        4. 保存配置文件和Profile文件
        5. 复制预设脚本到模拟目录
        
        Args:
            simulation_id: 模拟ID
            simulation_requirement: 模拟需求描述（用于LLM生成配置）
            document_text: 原始文档内容（用于LLM理解背景）
            defined_entity_types: 预定义的实体类型（可选）
            use_llm_for_profiles: 是否使用LLM生成详细人设
            progress_callback: 进度回调函数 (stage, progress, message)
            parallel_profile_count: 并行生成人设的数量，默认3
            
        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== 阶段1: 读取并过滤实体 ==========
            if progress_callback:
                progress_callback("reading", 0, "正在连接图谱...")
            
            reader = EntityReader()
            
            if progress_callback:
                progress_callback("reading", 30, "正在读取节点数据...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )
            
            state.entity_types = list(filtered.entity_types)
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "没有找到符合条件的实体，请检查图谱是否正确构建"
                self._save_simulation_state(state)
                return state
            
            # 按名称去重（图谱中可能存在同名实体），保留首次出现的实体
            seen_names = set()
            unique_entities = []
            for entity in filtered.entities:
                key = (entity.name or '').lower()
                if key and key in seen_names:
                    continue
                seen_names.add(key)
                unique_entities.append(entity)
            
            if len(unique_entities) < len(filtered.entities):
                logger.info(
                    f"实体去重: {len(filtered.entities)} -> {len(unique_entities)} "
                    f"（{len(filtered.entities) - len(unique_entities)} 个同名实体被合并）"
                )
            filtered.entities = unique_entities
            state.entities_count = len(unique_entities)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"完成，共 {state.entities_count} 个实体",
                    current=state.entities_count,
                    total=state.entities_count
                )
            
            # ========== 阶段2: 生成Agent Profile ==========
            total_entities = len(filtered.entities)
            
            # 如果是续生成模式，加载已有的 profiles
            existing_profiles_data = None
            if resume:
                try:
                    reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
                    if os.path.exists(reddit_path):
                        import json as _json
                        with open(reddit_path, 'r', encoding='utf-8') as f:
                            existing_profiles_data = _json.load(f)
                        logger.info(f"续生成模式：加载了 {len(existing_profiles_data)} 个已有 profiles")
                except Exception as e:
                    logger.warning(f"加载已有 profiles 失败，将全部重新生成: {e}")
                    existing_profiles_data = None
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    f"开始生成...{'（续生成模式）' if existing_profiles_data else ''}",
                    current=0,
                    total=total_entities
                )
            
            # 传入graph_id以启用图谱检索功能，获取更丰富的上下文
            generator = OasisProfileGenerator(graph_id=state.graph_id)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )
            
            # 设置实时保存的文件路径（优先使用 Reddit JSON 格式）
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id,  # 传入graph_id用于图谱检索
                parallel_count=parallel_profile_count,  # 并行生成数量
                realtime_output_path=realtime_output_path,  # 实时保存路径
                output_platform=realtime_platform,  # 输出格式
                existing_profiles=existing_profiles_data  # 续生成时传入已有 profiles
            )
            
            # 过滤掉 None（续生成时被 skip 的槽位为 None）
            valid_profiles = [p for p in profiles if p is not None]
            state.profiles_count = len(valid_profiles)
            
            # 保存Profile文件
            # 续生成模式下，realtime_output 已经合并了旧+新 profiles，
            # 这里只在非续生成时执行最终保存，避免用不完整列表覆盖已合并的文件。
            if not resume:
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 95, 
                        "保存Profile文件...",
                        current=total_entities,
                        total=total_entities
                    )
                
                if state.enable_reddit:
                    generator.save_profiles(
                        profiles=valid_profiles,
                        file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                        platform="reddit"
                    )
                
                if state.enable_twitter:
                    # Twitter使用CSV格式！这是OASIS的要求
                    generator.save_profiles(
                        profiles=valid_profiles,
                        file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                        platform="twitter"
                    )
            else:
                # 续生成模式：统计实际文件中的 profile 数量
                reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
                if os.path.exists(reddit_path):
                    import json as _json
                    with open(reddit_path, 'r', encoding='utf-8') as f:
                        state.profiles_count = len(_json.load(f))
                logger.info(f"续生成模式：跳过最终保存，文件已由实时写入维护（共 {state.profiles_count} 个）")
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 100, 
                    f"完成，共 {state.profiles_count} 个Profile",
                    current=state.profiles_count,
                    total=total_entities
                )
            
            # ========== 阶段3: LLM智能生成模拟配置 ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "正在分析模拟需求...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "正在调用LLM生成配置...",
                    current=1,
                    total=3
                )
            
            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit
            )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "正在保存配置文件...",
                    current=2,
                    total=3
                )
            
            # 保存配置文件
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "配置生成完成",
                    current=3,
                    total=3
                )
            
            # 注意：运行脚本保留在 backend/scripts/ 目录，不再复制到模拟目录
            # 启动模拟时，simulation_runner 会从 scripts/ 目录运行脚本
            
            # 更新状态
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"模拟准备完成: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"模拟准备失败: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """获取模拟状态"""
        return self._load_simulation_state(simulation_id)
    
    def delete_simulation(self, simulation_id: str) -> bool:
        """删除模拟（先停进程，再删目录）
        
        策略（Windows 友好）：
        1. 停进程 + 强杀 PID
        2. 主动关闭 Flask 进程内持有的所有文件句柄/引用（log 文件、world state engine 等）
        3. **先删 state.json**：这样即便部分日志文件被占用导致 rmtree 失败，
           历史列表也会立刻看不到这条记录（list_simulations 依赖 state.json 存在）
        4. 尝试 rmtree；失败时只要 state.json 已删，仍视为成功
        
        Args:
            simulation_id: 模拟ID
            
        Returns:
            是否删除成功（state.json 被删即视为成功）
        """
        import time
        # 注意：不使用 _get_simulation_dir，避免它的 os.makedirs 副作用重建目录
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return False
        
        # 1. 尝试通过 SimulationRunner 正常停止（若有 Popen 句柄）
        from .simulation_runner import SimulationRunner
        try:
            SimulationRunner.stop_simulation(simulation_id)
        except Exception as e:
            logger.warning(f"stop_simulation 失败（继续走强杀路径）: {e}")
        
        # 2. 兜底：直接用 PID 强杀（Flask 重启后 reattach 的孤儿子进程没有 Popen 句柄）
        run_state = SimulationRunner.get_run_state(simulation_id)
        pid = getattr(run_state, 'process_pid', None) if run_state else None
        if pid and SimulationRunner._pid_alive(pid):
            try:
                import signal
                if sys.platform == 'win32':
                    os.system(f'taskkill /F /T /PID {pid} >nul 2>&1')
                else:
                    os.kill(pid, signal.SIGKILL)
                logger.info(f"已强杀模拟进程: pid={pid}")
                # 等待句柄释放
                for _ in range(20):
                    if not SimulationRunner._pid_alive(pid):
                        break
                    time.sleep(0.2)
            except Exception as e:
                logger.warning(f"强杀进程 {pid} 失败: {e}")
        
        # 3. 主动关闭 Flask 进程内持有的文件句柄（Windows 删除失败的主要原因）
        try:
            fh = SimulationRunner._stdout_files.pop(simulation_id, None)
            if fh:
                try:
                    fh.close()
                except Exception:
                    pass
            fh = SimulationRunner._stderr_files.pop(simulation_id, None)
            if fh:
                try:
                    fh.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"关闭日志句柄失败（忽略）: {e}")
        
        # 4. 停止图谱记忆更新器（若启用）
        try:
            if SimulationRunner._graph_memory_enabled.get(simulation_id, False):
                from .graph_memory_updater import GraphMemoryManager
                try:
                    GraphMemoryManager.stop_updater(simulation_id)
                except Exception as e:
                    logger.warning(f"停止图谱记忆更新器失败（忽略）: {e}")
                SimulationRunner._graph_memory_enabled.pop(simulation_id, None)
        except Exception:
            pass
        
        # 5. 清除 Runner 的内存状态与引用（包括 world state engine / action buffer）
        try:
            SimulationRunner._run_states.pop(simulation_id, None)
            SimulationRunner._processes.pop(simulation_id, None)
            SimulationRunner._monitor_threads.pop(simulation_id, None)
            SimulationRunner._action_queues.pop(simulation_id, None) if hasattr(SimulationRunner, '_action_queues') else None
            SimulationRunner._world_state_engines.pop(simulation_id, None)
            SimulationRunner._round_action_buffers.pop(simulation_id, None)
        except Exception:
            pass
        
        # 6. 解除项目与该模拟的关联
        try:
            from ..models.project import ProjectManager
            state = self._load_simulation_state(simulation_id)
            if state and state.project_id:
                project = ProjectManager.get_project(state.project_id)
                if project and project.simulation_id == simulation_id:
                    project.simulation_id = None
                    ProjectManager.save_project(project)
                    logger.info(f"已解除项目 {state.project_id} 与模拟 {simulation_id} 的关联")
        except Exception as e:
            logger.warning(f"清理项目关联失败（忽略）: {e}")
        
        # 7. 清除 Manager 的内存缓存
        self._simulations.pop(simulation_id, None)
        
        # 8. 【关键】先删 state.json：使模拟立即从 list_simulations 消失
        #    即便后面 rmtree 因文件占用而失败，用户 UX 层面也是"已删除"
        state_file = os.path.join(sim_dir, "state.json")
        state_json_removed = False
        try:
            if os.path.exists(state_file):
                os.remove(state_file)
                state_json_removed = True
                logger.info(f"已删除 state.json: {state_file}")
        except Exception as e:
            logger.warning(f"删除 state.json 失败: {e}")
        
        # 9. 尝试删除整个目录（Windows 文件占用时重试几次，允许部分失败）
        def _on_rm_error(func, path, exc_info):
            try:
                os.chmod(path, 0o777)
                func(path)
            except Exception:
                pass
        
        # 轻度 gc 促使未引用的文件对象被关闭
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        
        last_err = None
        for attempt in range(5):
            try:
                shutil.rmtree(sim_dir, onerror=_on_rm_error)
                if not os.path.exists(sim_dir):
                    logger.info(f"已删除模拟目录: {sim_dir}")
                    return True
            except Exception as e:
                last_err = e
                logger.warning(f"rmtree 第{attempt+1}次失败: {e}")
            time.sleep(0.5 * (attempt + 1))
        
        # 10. 最后兜底：rmtree 失败时忽略错误删一次，尽量清空可删的文件
        try:
            shutil.rmtree(sim_dir, ignore_errors=True)
        except Exception:
            pass
        
        if not os.path.exists(sim_dir):
            logger.info(f"已删除模拟目录（忽略错误兜底）: {sim_dir}")
            return True
        
        # state.json 已删 → 列表层面已不可见，视为成功；残留文件用户可手动清理
        if state_json_removed:
            remaining = []
            try:
                for root, dirs, files in os.walk(sim_dir):
                    for name in files:
                        remaining.append(os.path.join(root, name))
                        if len(remaining) >= 10:
                            break
                    if len(remaining) >= 10:
                        break
            except Exception:
                pass
            logger.warning(
                f"模拟目录部分残留（state.json 已删，列表不再显示此记录）: {sim_dir}, "
                f"残留文件示例: {remaining}, 最后错误: {last_err}"
            )
            return True
        
        logger.error(f"删除模拟目录最终失败: {sim_dir}, 最后错误: {last_err}")
        return False
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """列出所有模拟"""
        simulations = []
        
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # 跳过隐藏文件（如 .DS_Store）和非目录文件
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """获取模拟的Agent Profile"""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        
        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        
        if not os.path.exists(profile_path):
            return []
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """获取模拟配置"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """获取运行说明"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. 激活conda环境: conda activate NexusMind\n"
                f"2. 运行模拟 (脚本位于 {scripts_dir}):\n"
                f"   - 单独运行Twitter: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - 单独运行Reddit: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - 并行运行双平台: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
