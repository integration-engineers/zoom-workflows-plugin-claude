#!/usr/bin/env python3
"""Recompile one carried workflow through the current planner_v3 palette."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from compile_workflow import compile_plan

_SCHEMA_VERSION = "planner_v3.workflow_recompile_update.v2"
_SOURCE_SCHEMA_VERSION = "planner_v3.workflow_update_source.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value


def _load_source(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    source = _load_json(path)
    if source.get("schema_version") != _SOURCE_SCHEMA_VERSION:
        raise ValueError("update source schema version is unsupported")
    workflow = source.get("workflow")
    envelope = source.get("workflow_envelope")
    source_digest = source.get("source_digest")
    if (
        not isinstance(workflow, dict)
        or not isinstance(envelope, dict)
        or not isinstance(source_digest, str)
    ):
        raise ValueError("update source is incomplete")
    if _digest(workflow) != source_digest:
        raise ValueError("update source digest mismatch")
    return workflow, envelope, source_digest


def _load_update_plan(path: Path, *, expected_digest: str) -> dict[str, Any]:
    update_plan = _load_json(path)
    if set(update_plan) != {"schema_version", "source_digest", "plan"}:
        raise ValueError("update plan contains unsupported fields")
    if update_plan.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("update plan schema version is unsupported")
    if update_plan.get("source_digest") != expected_digest:
        raise ValueError("update plan source digest is stale")
    plan = update_plan.get("plan")
    if not isinstance(plan, dict):
        raise ValueError("update plan requires a regular planner_v3 PlanIR object")
    return plan


def _compiled_flow(compiled: dict[str, Any]) -> dict[str, Any]:
    data = compiled.get("data")
    flows = data.get("flows") if isinstance(data, dict) else None
    if not isinstance(flows, list) or len(flows) != 1 or not isinstance(flows[0], dict):
        raise ValueError("compiled update must contain exactly one workflow")
    return deepcopy(flows[0])


def _apply_source_identity(
    *,
    source_workflow: dict[str, Any],
    source_envelope: dict[str, Any],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    candidate = _compiled_flow(compiled)
    for key, value in source_workflow.items():
        if key == "workflow_metadata":
            source_metadata = deepcopy(value)
            compiled_metadata = candidate.get("workflow_metadata")
            if not isinstance(source_metadata, dict) or not isinstance(compiled_metadata, dict):
                raise ValueError("compiled update workflow metadata is invalid")
            description = compiled_metadata.get("description")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("compiled update requires a semantic description")
            source_metadata["description"] = description.strip()
            candidate[key] = source_metadata
        elif key not in {"nodes", "edges"}:
            candidate[key] = deepcopy(value)

    output = deepcopy(source_envelope)
    data = output.get("data")
    if not isinstance(data, dict):
        raise ValueError("update source envelope data is invalid")
    data["flows"] = [candidate]
    outer_metadata = data.get("metadata")
    if isinstance(outer_metadata, dict):
        outer_metadata["description"] = candidate["workflow_metadata"]["description"]
    return output


def _write_atomic(path: Path, value: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary.write_bytes(content)
    temporary.replace(path)
    return content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--allow-html-node",
        action="store_true",
        help="allow HTML nodes for a server-authorized semantic update",
    )
    args = parser.parse_args()

    source_workflow, source_envelope, source_digest = _load_source(Path(args.source))
    plan = _load_update_plan(Path(args.plan), expected_digest=source_digest)
    result = compile_plan(plan, allow_html_node=args.allow_html_node)
    if result.get("status") != "compiled" or not isinstance(result.get("workflow"), dict):
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "findings": result.get("findings") or ["workflow compilation failed"],
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1

    output = _apply_source_identity(
        source_workflow=source_workflow,
        source_envelope=source_envelope,
        compiled=result["workflow"],
    )
    candidate = output["data"]["flows"][0]
    output_bytes = _write_atomic(Path(args.output), output)
    print(
        json.dumps(
            {
                "status": "updated",
                "source_digest": source_digest,
                "candidate_digest": "sha256:" + hashlib.sha256(output_bytes).hexdigest(),
                "node_count": len(candidate.get("nodes") or []),
                "edge_count": len(candidate.get("edges") or []),
                "node_types": sorted(
                    {
                        str(node.get("node_type"))
                        for node in candidate.get("nodes") or []
                        if isinstance(node, dict)
                    }
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
