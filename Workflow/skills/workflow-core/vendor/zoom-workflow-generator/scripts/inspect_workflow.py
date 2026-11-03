#!/usr/bin/env python3
"""Inspect a staged existing workflow without modifying it."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _load_source(path: Path) -> tuple[dict[str, Any], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("update source must be an object")
    if payload.get("schema_version") != "planner_v3.workflow_update_source.v1":
        raise ValueError("update source schema version is unsupported")
    workflow = payload.get("workflow")
    expected_digest = payload.get("source_digest")
    if not isinstance(workflow, dict) or not isinstance(expected_digest, str):
        raise ValueError("update source is incomplete")
    actual_digest = "sha256:" + hashlib.sha256(_canonical_bytes(workflow)).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("update source digest does not match its workflow")
    return workflow, actual_digest


def _edge_endpoint(edge: Mapping[str, Any], primary: str, fallback: str) -> object:
    return edge.get(primary, edge.get(fallback))


def _node_summary(
    node: Mapping[str, Any],
    *,
    incoming: list[str],
    outgoing: list[str],
) -> dict[str, Any]:
    input_map = node.get("input_map")
    config = node.get("config")
    return {
        "reference_id": node.get("reference_id"),
        "node_id": node.get("node_id"),
        "node_type": node.get("node_type"),
        "node_name": node.get("node_name"),
        "node_desc": node.get("node_desc"),
        "prompt": node.get("prompt"),
        "input_fields": sorted(input_map) if isinstance(input_map, dict) else [],
        "config_fields": sorted(config) if isinstance(config, dict) else [],
        "incoming_references": incoming,
        "outgoing_references": outgoing,
    }


def _bounded_node_view(node: Mapping[str, Any]) -> dict[str, Any]:
    input_map = node.get("input_map")
    bounded_input: dict[str, Any] = {}
    if isinstance(input_map, dict):
        for key, value in input_map.items():
            if key in {"tools", "skills"} and isinstance(value, list):
                bounded_input[key] = {"item_count": len(value), "omitted_from_view": True}
            else:
                bounded_input[key] = value
    return {
        "reference_id": node.get("reference_id"),
        "node_id": node.get("node_id"),
        "node_type": node.get("node_type"),
        "node_name": node.get("node_name"),
        "node_desc": node.get("node_desc"),
        "prompt": node.get("prompt"),
        "input_map": bounded_input,
        "config": node.get("config", {}),
        "output_schema": node.get("output_schema", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--all-details", action="store_true")
    args = parser.parse_args()

    workflow, source_digest = _load_source(Path(args.source))
    nodes = workflow.get("nodes")
    edges = workflow.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("update source requires nodes and edges")

    if args.reference:
        matches = [
            node
            for node in nodes
            if isinstance(node, Mapping) and node.get("reference_id") == args.reference
        ]
        if len(matches) != 1:
            raise ValueError("reference must identify exactly one source node")
        print(json.dumps(_bounded_node_view(matches[0]), ensure_ascii=False, indent=2))
        return 0

    if args.all_details:
        metadata = workflow.get("workflow_metadata")
        print(
            json.dumps(
                {
                    "source_digest": source_digest,
                    "workflow_metadata": metadata if isinstance(metadata, Mapping) else {},
                    "form": workflow.get("form")
                    if isinstance(workflow.get("form"), Mapping)
                    else {},
                    "nodes": [
                        _bounded_node_view(node) for node in nodes if isinstance(node, Mapping)
                    ],
                    "edges": edges,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    summaries = []
    for node in nodes:
        if not isinstance(node, Mapping):
            raise ValueError("update source nodes must be objects")
        reference_id = node.get("reference_id")
        incoming = [
            str(_edge_endpoint(edge, "source_node", "source"))
            for edge in edges
            if isinstance(edge, Mapping)
            and _edge_endpoint(edge, "target_node", "target") == reference_id
        ]
        outgoing = [
            str(_edge_endpoint(edge, "target_node", "target"))
            for edge in edges
            if isinstance(edge, Mapping)
            and _edge_endpoint(edge, "source_node", "source") == reference_id
        ]
        summaries.append(_node_summary(node, incoming=incoming, outgoing=outgoing))
    metadata = workflow.get("workflow_metadata")
    print(
        json.dumps(
            {
                "source_digest": source_digest,
                "workflow_name": metadata.get("name") if isinstance(metadata, Mapping) else None,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "nodes": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
