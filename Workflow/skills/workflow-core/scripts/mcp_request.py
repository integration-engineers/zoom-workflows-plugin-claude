#!/usr/bin/env python3
"""Turn one exported workflow into the arguments of a live Workflow MCP test or deploy call."""
from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import sys
import uuid
from pathlib import Path

NODE_KEYS = {
    "children", "config", "expanded", "hidden", "input_map", "node_alias", "node_id", "node_name",
    "node_set_id", "node_type", "output_schema", "position", "reference_id",
}
EDGE_KEYS = {"condition", "source_node", "target_node"}
METADATA_KEYS = {
    "test": ("name",),
    "create": ("name", "description", "icon"),
    "update": ("flow_id", "name", "description", "icon", "template_id"),
}
GUID_RE = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")


def _normalize_trigger_input(trigger_input: dict) -> dict:
    data = ((trigger_input.get("meeting") or {}).get("data")) if isinstance(trigger_input, dict) else None
    value = data.get("meeting_uuid") if isinstance(data, dict) else None
    if isinstance(value, str) and GUID_RE.match(value.strip()):
        trigger_input = copy.deepcopy(trigger_input)
        trigger_input["meeting"]["data"]["meeting_uuid"] = base64.b64encode(uuid.UUID(value.strip()).bytes).decode("ascii")
    return trigger_input


def _flow(payload: dict) -> dict:
    if all(key in payload for key in ("workflow_metadata", "nodes", "edges")):
        return copy.deepcopy(payload)
    flows = (payload.get("data") or {}).get("flows")
    if not (isinstance(flows, list) and len(flows) == 1 and isinstance(flows[0], dict)):
        raise ValueError("expected one flow or an export bundle with exactly one flow")
    return copy.deepcopy(flows[0])


def build(payload: dict, op: str, *, flow_id: str | None = None, trigger_input: dict | None = None) -> dict:
    flow = _flow(payload)
    metadata = flow.get("workflow_metadata")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        raise ValueError("workflow_metadata.name is required")
    if op not in METADATA_KEYS:
        raise ValueError(op)
    if op == "update" and (not flow_id or metadata.get("flow_id") != flow_id):
        raise ValueError("update needs --flow-id equal to the flow_id in the fetched definition")
    args = {
        "nodes": [{key: value for key, value in node.items() if key in NODE_KEYS} for node in flow["nodes"]],
        "edges": [{key: value for key, value in edge.items() if key in EDGE_KEYS} for edge in flow["edges"]],
        "workflow_metadata": {key: metadata[key] for key in METADATA_KEYS[op] if key in metadata},
    }
    if op == "test" and trigger_input is not None:
        args["trigger_input"] = _normalize_trigger_input(trigger_input)
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("op", choices=tuple(METADATA_KEYS))
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="where to write the tool arguments")
    parser.add_argument("--flow-id", help="update only: the flow_id from list or the user's choice")
    parser.add_argument("--trigger-input", type=Path, help="test only: transient trigger input JSON")
    args = parser.parse_args()
    try:
        payload = json.loads(args.workflow.read_text(encoding="utf-8"))
        trigger = json.loads(args.trigger_input.read_text(encoding="utf-8")) if args.trigger_input else None
        result = build(payload, args.op, flow_id=args.flow_id, trigger_input=trigger)
        text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "out": str(args.out.resolve()), "bytes": len(text.encode("utf-8")),
        "nodes": len(result["nodes"]), "edges": len(result["edges"]),
        "workflow_metadata": sorted(result["workflow_metadata"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
