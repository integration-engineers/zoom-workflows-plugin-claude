#!/usr/bin/env python3
"""Stage one fetched workflow definition and emit the host-supplied update arguments."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

_SOURCE_SCHEMA_VERSION = "planner_v3.workflow_update_source.v1"
_MODE = "declarative_workflow_update_only"
_PLUGIN_ROOT = Path(__file__).resolve().parents[4]


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_flow(workflow: object) -> dict[str, Any]:
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be an object")
    if not isinstance(workflow.get("workflow_metadata"), dict):
        raise ValueError("workflow requires workflow_metadata")
    nodes, edges = workflow.get("nodes"), workflow.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("workflow requires nodes and edges arrays")
    references: set[str] = set()
    for node in nodes:
        reference = node.get("reference_id") if isinstance(node, dict) else None
        if not isinstance(reference, str) or not reference or reference in references:
            raise ValueError("workflow nodes require unique reference_id values")
        references.add(reference)
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("workflow edges must be objects")
        if edge.get("source_node", edge.get("source")) not in references or edge.get(
            "target_node", edge.get("target")
        ) not in references:
            raise ValueError("workflow edge endpoint is invalid")
    return deepcopy(workflow)


def _extract(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    data = payload.get("data")
    flows = data.get("flows") if isinstance(data, dict) else None
    if flows is not None:
        if not isinstance(flows, list) or len(flows) != 1:
            raise ValueError("workflow export must contain exactly one flow")
        return _validate_flow(flows[0]), deepcopy(payload)
    workflow = _validate_flow(payload)
    metadata = workflow["workflow_metadata"]
    envelope = {
        "version": 1,
        "data": {
            "metadata": {
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
            },
            "flows": [deepcopy(workflow)],
        },
    }
    return workflow, envelope


def _outside_plugin(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == _PLUGIN_ROOT or _PLUGIN_ROOT in resolved.parents:
        raise ValueError("update files must be outside the plugin tree")
    return resolved


def _write_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="definition returned by get-definition")
    parser.add_argument("--flow-id", required=True, help="flow_id that was fetched this turn")
    parser.add_argument("--workdir", required=True, help="absolute request-workspace directory")
    args = parser.parse_args()

    workdir = _outside_plugin(Path(args.workdir))
    payload = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("workflow source must be a JSON object")
    workflow, envelope = _extract(payload)
    flow_id = workflow["workflow_metadata"].get("flow_id")
    if flow_id != args.flow_id:
        raise ValueError("fetched definition does not carry the requested flow_id")

    source_digest = _digest(workflow)
    suffix = source_digest.removeprefix("sha256:")[:16]
    basename = f"planner_v3_existing_workflow_{suffix}.json"
    staged_path = workdir / basename
    output_path = workdir / f"workflow_update_{suffix}.json"
    _write_atomic(
        staged_path,
        {
            "schema_version": _SOURCE_SCHEMA_VERSION,
            "source_digest": source_digest,
            "workflow": workflow,
            "workflow_envelope": envelope,
        },
    )
    print(
        json.dumps(
            {
                "status": "staged",
                "flow_id": flow_id,
                "source_path": str(staged_path),
                "node_count": len(workflow["nodes"]),
                "edge_count": len(workflow["edges"]),
                "skill_arguments": {
                    "mode": _MODE,
                    "output_path": str(output_path),
                    "source_attachment_basename": basename,
                    "source_digest": source_digest,
                },
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, separators=(",", ":")))
        sys.exit(1)
