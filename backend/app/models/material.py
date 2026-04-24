"""
种子材料管理
支持向已有项目持续追加材料，每批材料可追溯来源与时间
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from ..config import Config


@dataclass
class MaterialEntry:
    """单条种子材料"""
    material_id: str
    project_id: str
    source_type: str  # file | web | manual | official_notice | media_report | social_post
    title: str
    ingested_at: str

    # 可选
    source_url: Optional[str] = None
    source_time: Optional[str] = None          # 材料所描述事件的真实发生时间
    saved_filename: Optional[str] = None       # raw/ 下的文件名
    extracted_text_path: Optional[str] = None  # extracted/<material_id>.txt
    credibility: float = 1.0                   # 0-1，默认可信
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    used_in_baseline_ids: List[str] = field(default_factory=list)
    text_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "project_id": self.project_id,
            "source_type": self.source_type,
            "title": self.title,
            "ingested_at": self.ingested_at,
            "source_url": self.source_url,
            "source_time": self.source_time,
            "saved_filename": self.saved_filename,
            "extracted_text_path": self.extracted_text_path,
            "credibility": self.credibility,
            "tags": self.tags,
            "summary": self.summary,
            "used_in_baseline_ids": self.used_in_baseline_ids,
            "text_length": self.text_length,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialEntry":
        return cls(
            material_id=data["material_id"],
            project_id=data["project_id"],
            source_type=data.get("source_type", "file"),
            title=data.get("title", ""),
            ingested_at=data.get("ingested_at", ""),
            source_url=data.get("source_url"),
            source_time=data.get("source_time"),
            saved_filename=data.get("saved_filename"),
            extracted_text_path=data.get("extracted_text_path"),
            credibility=data.get("credibility", 1.0),
            tags=data.get("tags", []),
            summary=data.get("summary"),
            used_in_baseline_ids=data.get("used_in_baseline_ids", []),
            text_length=data.get("text_length", 0),
        )


class MaterialManager:
    """
    材料管理器

    目录结构（在已有 project 目录下追加）：
        uploads/projects/<project_id>/
          materials/
            manifest.json          ← 材料清单
            raw/<material_id>_<filename>
            extracted/<material_id>.txt
    """

    MATERIALS_SUBDIR = "materials"
    RAW_SUBDIR = "raw"
    EXTRACTED_SUBDIR = "extracted"
    MANIFEST_FILE = "manifest.json"

    # ── 路径工具 ──

    @classmethod
    def _project_dir(cls, project_id: str) -> str:
        return os.path.join(Config.UPLOAD_FOLDER, "projects", project_id)

    @classmethod
    def _materials_dir(cls, project_id: str) -> str:
        return os.path.join(cls._project_dir(project_id), cls.MATERIALS_SUBDIR)

    @classmethod
    def _raw_dir(cls, project_id: str) -> str:
        return os.path.join(cls._materials_dir(project_id), cls.RAW_SUBDIR)

    @classmethod
    def _extracted_dir(cls, project_id: str) -> str:
        return os.path.join(cls._materials_dir(project_id), cls.EXTRACTED_SUBDIR)

    @classmethod
    def _manifest_path(cls, project_id: str) -> str:
        return os.path.join(cls._materials_dir(project_id), cls.MANIFEST_FILE)

    @classmethod
    def _ensure_dirs(cls, project_id: str) -> None:
        os.makedirs(cls._raw_dir(project_id), exist_ok=True)
        os.makedirs(cls._extracted_dir(project_id), exist_ok=True)

    # ── 清单读写 ──

    @classmethod
    def _load_manifest(cls, project_id: str) -> List[Dict[str, Any]]:
        path = cls._manifest_path(project_id)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _save_manifest(cls, project_id: str, entries: List[Dict[str, Any]]) -> None:
        cls._ensure_dirs(project_id)
        path = cls._manifest_path(project_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    # ── 公共 API ──

    @classmethod
    def add_material(
        cls,
        project_id: str,
        *,
        title: str,
        source_type: str = "file",
        source_url: Optional[str] = None,
        source_time: Optional[str] = None,
        credibility: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> MaterialEntry:
        """
        创建一条材料记录（元数据），返回 MaterialEntry。
        文件保存与文本提取由调用方后续完成。
        """
        cls._ensure_dirs(project_id)

        material_id = f"mat_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        entry = MaterialEntry(
            material_id=material_id,
            project_id=project_id,
            source_type=source_type,
            title=title,
            ingested_at=now,
            source_url=source_url,
            source_time=source_time,
            credibility=credibility,
            tags=tags or [],
        )

        # 追加到 manifest
        manifest = cls._load_manifest(project_id)
        manifest.append(entry.to_dict())
        cls._save_manifest(project_id, manifest)

        return entry

    @classmethod
    def save_raw_file(cls, project_id: str, material_id: str, file_storage, original_filename: str) -> str:
        """
        保存原始文件到 materials/raw/，返回保存后的文件名。
        """
        cls._ensure_dirs(project_id)
        ext = os.path.splitext(original_filename)[1].lower()
        saved_name = f"{material_id}_{uuid.uuid4().hex[:6]}{ext}"
        dest = os.path.join(cls._raw_dir(project_id), saved_name)
        file_storage.save(dest)
        return saved_name

    @classmethod
    def save_extracted_text(cls, project_id: str, material_id: str, text: str) -> str:
        """
        保存提取的文本到 materials/extracted/<material_id>.txt，返回相对路径。
        """
        cls._ensure_dirs(project_id)
        filename = f"{material_id}.txt"
        dest = os.path.join(cls._extracted_dir(project_id), filename)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        return filename

    @classmethod
    def update_material(cls, project_id: str, material_id: str, **kwargs) -> Optional[MaterialEntry]:
        """
        更新某条材料的字段（saved_filename / extracted_text_path / summary / text_length 等）。
        """
        manifest = cls._load_manifest(project_id)
        for item in manifest:
            if item["material_id"] == material_id:
                item.update(kwargs)
                cls._save_manifest(project_id, manifest)
                return MaterialEntry.from_dict(item)
        return None

    @classmethod
    def get_material(cls, project_id: str, material_id: str) -> Optional[MaterialEntry]:
        manifest = cls._load_manifest(project_id)
        for item in manifest:
            if item["material_id"] == material_id:
                return MaterialEntry.from_dict(item)
        return None

    @classmethod
    def list_materials(cls, project_id: str) -> List[MaterialEntry]:
        """返回按接入时间正序排列的材料列表。"""
        manifest = cls._load_manifest(project_id)
        entries = [MaterialEntry.from_dict(d) for d in manifest]
        entries.sort(key=lambda e: e.ingested_at)
        return entries

    @classmethod
    def get_combined_text(cls, project_id: str, material_ids: Optional[List[str]] = None) -> str:
        """
        合并指定材料（或全部材料）的提取文本，按接入时间排序拼接。
        """
        entries = cls.list_materials(project_id)
        if material_ids:
            entries = [e for e in entries if e.material_id in material_ids]

        parts: List[str] = []
        for entry in entries:
            if entry.extracted_text_path:
                full_path = os.path.join(cls._extracted_dir(project_id), os.path.basename(entry.extracted_text_path))
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        parts.append(f.read())
        return "\n\n".join(parts)

    @classmethod
    def count(cls, project_id: str) -> int:
        return len(cls._load_manifest(project_id))
