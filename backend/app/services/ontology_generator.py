"""
Ontology generation service for NexusMind event-memory graphs.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

MAX_ENTITY_TYPES = 10
MAX_EDGE_TYPES = 10
MAX_TEXT_LENGTH_FOR_LLM = 50000
RESERVED_ATTRIBUTE_NAMES = {"name", "uuid", "group_id", "created_at", "summary"}

FALLBACK_ENTITY_TYPES = [
    {
        "name": "Person",
        "description": "Any individual person not fitting other specific person types.",
        "attributes": [
            {"name": "full_name", "type": "text", "description": "Full name of the person"},
            {"name": "role", "type": "text", "description": "Role or occupation"},
        ],
        "examples": ["ordinary citizen", "anonymous netizen"],
    },
    {
        "name": "Organization",
        "description": "Any organization not fitting other specific organization types.",
        "attributes": [
            {"name": "org_name", "type": "text", "description": "Name of the organization"},
            {"name": "org_type", "type": "text", "description": "Type of organization"},
        ],
        "examples": ["small business", "community group"],
    },
]

ONTOLOGY_SYSTEM_PROMPT = """You are NexusMind's ontology designer for public-opinion event simulation.
Return one valid JSON object only. Do not add markdown or explanation.

Required schema:
{
  "entity_types": [
    {
      "name": "EnglishPascalCase",
      "description": "short English description, <= 100 chars",
      "attributes": [{"name": "english_snake_case", "type": "text", "description": "..."}],
      "examples": ["example actor from the material"]
    }
  ],
  "edge_types": [
    {
      "name": "ENGLISH_UPPER_SNAKE_CASE",
      "description": "short English description, <= 100 chars",
      "source_targets": [{"source": "EntityType", "target": "EntityType"}],
      "attributes": []
    }
  ],
  "event_name": "short Chinese event name if the material is Chinese",
  "analysis_summary": "brief material analysis; use Chinese for Chinese material"
}

Rules:
1. Design exactly 10 entity types. The last two must be Person and Organization fallback types.
2. The first eight should be concrete actors in the event, such as students, teachers, universities, media, regulators, family members, alumni, platforms, or other active stakeholders.
3. Entity types must represent real actors that can speak, respond, transmit information, or affect the event. Do not use abstract concepts like emotion, topic, trend, policy, or risk as entities.
4. Design 6-10 edge types for observable relations such as affiliation, response, report, regulation, support, opposition, collaboration, conflict, and information diffusion.
5. Attribute names must be English snake_case and must not use name, uuid, group_id, created_at, or summary.
6. Entity names must be English PascalCase; edge names must be English UPPER_SNAKE_CASE.
"""


def _to_pascal_case(name: str) -> str:
    parts = []
    for chunk in re.split(r'[^0-9A-Za-z]+', str(name or '')):
        parts.extend(re.sub(r'([a-z])([A-Z])', r'\1_\2', chunk).split('_'))
    value = ''.join(part[:1].upper() + part[1:].lower() for part in parts if part)
    return value or 'Unknown'


def _to_upper_snake(name: str) -> str:
    value = re.sub(r'([a-z])([A-Z])', r'\1_\2', str(name or ''))
    value = re.sub(r'[^0-9A-Za-z]+', '_', value)
    value = re.sub(r'_+', '_', value).strip('_')
    return value.upper() or 'UNKNOWN_RELATION'


def _safe_attribute_name(name: str, fallback_index: int) -> str:
    attr = re.sub(r'[^0-9A-Za-z]+', '_', str(name or '')).strip('_').lower()
    if not attr or attr in RESERVED_ATTRIBUTE_NAMES:
        attr = f"attribute_{fallback_index}"
    if attr[0].isdigit():
        attr = f"field_{attr}"
    return attr


def _limit_description(value: Any) -> str:
    text = str(value or '')
    return text if len(text) <= 100 else text[:97] + '...'


def _json_literal(value: str) -> str:
    return json.dumps(str(value or ''), ensure_ascii=False)


class OntologyGenerator:
    """
    Ontology generator for event simulation graphs.
    """

    MAX_TEXT_LENGTH_FOR_LLM = MAX_TEXT_LENGTH_FOR_LLM

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message(document_texts, simulation_requirement, additional_context)},
        ]
        raw_result = self.llm_client.chat_json(messages=messages, temperature=0.3, max_tokens=4096)
        return self._validate_and_process(raw_result)

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        combined_text = "\n\n---\n\n".join(document_texts or [])
        original_length = len(combined_text)
        if original_length > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(source text length={original_length}, truncated to {self.MAX_TEXT_LENGTH_FOR_LLM} chars for ontology design)..."

        sections = [
            "## Simulation Goal",
            simulation_requirement or "Not provided",
            "## Seed Materials",
            combined_text or "Not provided",
        ]
        if additional_context:
            sections.extend(["## Additional Context", additional_context])
        sections.append("Design the ontology around actionable actors, observable relations, and future public-opinion simulation needs.")
        return "\n\n".join(sections)

    def _normalize_attributes(self, attributes: Any) -> List[Dict[str, str]]:
        normalized = []
        if not isinstance(attributes, list):
            return normalized
        for index, attr in enumerate(attributes[:3], 1):
            if not isinstance(attr, dict):
                continue
            normalized.append({
                "name": _safe_attribute_name(attr.get("name", ""), index),
                "type": attr.get("type") or "text",
                "description": str(attr.get("description") or attr.get("name") or "attribute"),
            })
        return normalized

    def _normalize_entity(self, entity: Dict[str, Any], aliases: Dict[str, str]) -> Optional[Dict[str, Any]]:
        original_name = entity.get("name")
        name = _to_pascal_case(original_name)
        if not name:
            return None
        aliases[str(original_name)] = name
        aliases[name] = name
        return {
            "name": name,
            "description": _limit_description(entity.get("description", f"A {name} entity.")),
            "attributes": self._normalize_attributes(entity.get("attributes", [])),
            "examples": entity.get("examples", []) if isinstance(entity.get("examples", []), list) else [],
        }

    def _normalize_edge(self, edge: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
        name = _to_upper_snake(edge.get("name"))
        source_targets = []
        for item in edge.get("source_targets", []) or []:
            if not isinstance(item, dict):
                continue
            source = aliases.get(str(item.get("source")), _to_pascal_case(item.get("source")))
            target = aliases.get(str(item.get("target")), _to_pascal_case(item.get("target")))
            source_targets.append({"source": source, "target": target})
        return {
            "name": name,
            "description": _limit_description(edge.get("description", f"A {name} relationship.")),
            "source_targets": source_targets,
            "attributes": self._normalize_attributes(edge.get("attributes", [])),
        }

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        result = result if isinstance(result, dict) else {}
        aliases: Dict[str, str] = {}
        entities = []
        seen_entities = set()
        for raw_entity in result.get("entity_types", []) or []:
            if not isinstance(raw_entity, dict):
                continue
            entity = self._normalize_entity(raw_entity, aliases)
            if entity and entity["name"] not in seen_entities:
                seen_entities.add(entity["name"])
                entities.append(entity)

        fallback_names = {item["name"] for item in FALLBACK_ENTITY_TYPES}
        specific_entities = [item for item in entities if item["name"] not in fallback_names]
        fallback_by_name = {item["name"]: item for item in FALLBACK_ENTITY_TYPES}
        for entity in entities:
            if entity["name"] in fallback_names:
                fallback_by_name[entity["name"]] = entity

        result["entity_types"] = specific_entities[:MAX_ENTITY_TYPES - 2] + [
            fallback_by_name["Person"],
            fallback_by_name["Organization"],
        ]
        aliases.update({entity["name"]: entity["name"] for entity in result["entity_types"]})

        edges = []
        seen_edges = set()
        for raw_edge in result.get("edge_types", []) or []:
            if not isinstance(raw_edge, dict):
                continue
            edge = self._normalize_edge(raw_edge, aliases)
            if edge["name"] not in seen_edges:
                seen_edges.add(edge["name"])
                edges.append(edge)
        result["edge_types"] = edges[:MAX_EDGE_TYPES]
        result.setdefault("analysis_summary", "")
        result.setdefault("event_name", "")
        return result

    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        code_lines = [
            '"""',
            'Custom entity and edge type definitions generated by NexusMind.',
            '"""',
            '',
            'from pydantic import BaseModel, Field',
            'from typing import Optional',
            '',
            'EntityModel = BaseModel',
            'EdgeModel = BaseModel',
            'EntityText = Optional[str]',
            '',
            '# Entity type definitions',
            '',
        ]
        for entity in ontology.get("entity_types", []):
            name = _to_pascal_case(entity.get("name"))
            description = _json_literal(entity.get("description", f"A {name} entity."))[1:-1]
            code_lines.extend([f'class {name}(EntityModel):', f'    """{description}"""'])
            attrs = self._normalize_attributes(entity.get("attributes", []))
            if attrs:
                for attr in attrs:
                    code_lines.extend([
                        f'    {attr["name"]}: EntityText = Field(',
                        f'        description={_json_literal(attr["description"])},',
                        '        default=None',
                        '    )',
                    ])
            else:
                code_lines.append('    pass')
            code_lines.extend(['', ''])

        code_lines.extend(['# Edge type definitions', ''])
        for edge in ontology.get("edge_types", []):
            relation_name = _to_upper_snake(edge.get("name"))
            class_name = _to_pascal_case(relation_name)
            description = _json_literal(edge.get("description", f"A {relation_name} relationship."))[1:-1]
            code_lines.extend([f'class {class_name}(EdgeModel):', f'    """{description}"""'])
            attrs = self._normalize_attributes(edge.get("attributes", []))
            if attrs:
                for attr in attrs:
                    code_lines.extend([
                        f'    {attr["name"]}: EntityText = Field(',
                        f'        description={_json_literal(attr["description"])},',
                        '        default=None',
                        '    )',
                    ])
            else:
                code_lines.append('    pass')
            code_lines.extend(['', ''])

        code_lines.extend(['ENTITY_TYPES = {'])
        for entity in ontology.get("entity_types", []):
            name = _to_pascal_case(entity.get("name"))
            code_lines.append(f'    "{name}": {name},')
        code_lines.extend(['}', '', 'EDGE_TYPES = {'])
        for edge in ontology.get("edge_types", []):
            relation_name = _to_upper_snake(edge.get("name"))
            code_lines.append(f'    "{relation_name}": {_to_pascal_case(relation_name)},')
        code_lines.extend(['}', '', 'EDGE_SOURCE_TARGETS = {'])
        for edge in ontology.get("edge_types", []):
            relation_name = _to_upper_snake(edge.get("name"))
            pairs = [
                f'{{"source": "{_to_pascal_case(pair.get("source"))}", "target": "{_to_pascal_case(pair.get("target"))}"}}'
                for pair in edge.get("source_targets", []) or []
                if isinstance(pair, dict)
            ]
            if pairs:
                code_lines.append(f'    "{relation_name}": [{", ".join(pairs)}],')
        code_lines.append('}')
        return '\n'.join(code_lines)
