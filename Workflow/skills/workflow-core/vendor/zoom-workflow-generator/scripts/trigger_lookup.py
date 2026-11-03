#!/usr/bin/env python3
"""Authoring view of resources/phase1_node_catalog.json for choosing a PlanIR trigger.

  --list                       one compact entry per trigger (node_id, outputs, config, input_map)
  --node-id ID [--event NAME]  one trigger's PlanIR-shaped config, argument schema, and outputs

Everything is derived at run time from the catalog and the compiler's own constants, so it
cannot drift from what compile_workflow.py accepts. The catalog stays the compiler's input.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import sys
from pathlib import Path

GEN = Path(__file__).resolve().parents[1]
CATALOG = GEN / "resources" / "phase1_node_catalog.json"

OVERLAY = {
    "zm.system.rss.feed": {
        "input_map": [
            "feed_urls: [http(s) URL, ...] required, unique, order kept",
            "poll_interval_minutes: int 1..1440, default 15",
        ],
        "note": "semantic PlanIR keys; the compiler emits appKey/inputValues (_rss_trigger_input_map)",
    },
    "zm.system.manual.trigger_form": {
        "input_map": [
            "form: [{name, type, description, required, default_value?}] - smallest set of run-time fields",
        ],
        "outputs": "each form[].name becomes {{trigger.<name>}} (_form_output_schema)",
    },
    "zm.system.scheduler.trigger.scheduler": {
        "input_map": [
            "ALL 10 keys required: startsOn 'YYYY-MM-DD HH:mm:ss' (next future run); timezone IANA (profile tz or UTC)",
            "frequency: -1 once | 0 daily | 1 one weekday weekly | 2 every weekday | 3 monthly (also 'first Monday') "
            "| 4 annually | 5 custom (several weekdays, every-N-weeks, hourly)",
            "repeatLevel: hour|day|week|month|year; repeatEvery: int >=1 (0 only for once)",
            "repeatOn: weekly day list 1=Sun..7=Sat, [] otherwise; monthlyOn: 1-31, 0 otherwise",
            "endType: -1 never | 1 date (endDate) | 2 times (executedTimes); unbounded => endDate \"\", executedTimes 0",
            "daily 0/day/1/[]; weekly 1/week/1/[d]; weekdays 2/week/1/[]; hourly poll 5/hour/1/[]",
        ],
    },
    "zm.tc.channel.trigger.emoji_reaction": {
        "note": "emojis = base64 of UTF-8 bytes; 'when I react' => specifiedChannelsWithMe=true; no channel named => "
        "allChannels=true, channelInfos=[]",
    },
}


def load_compiler():
    spec = importlib.util.spec_from_file_location("compile_workflow", GEN / "scripts" / "compile_workflow.py")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def triggers() -> list[dict]:
    return [item for item in json.loads(CATALOG.read_text(encoding="utf-8"))["items"] if item.get("node_type") == "trigger"]


def other_items() -> list[str]:
    return [item["node_id"] for item in json.loads(CATALOG.read_text(encoding="utf-8"))["items"]
            if item.get("node_type") != "trigger"]


def _short(text: str, limit: int = 110) -> str:
    text = " ".join(str(text or "").replace("\\n", " ").split())
    for prefix in ("Zoom Meetings - ", "Zoom Team Chat - ", "Zoom System Utilities - "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    sentences = [s.strip().rstrip(".") for s in text.split(". ") if s.strip()]
    sentences = [s for s in sentences if not s.lower().endswith(("trigger node", "trigger"))] or sentences
    first = sentences[0] if sentences else ""
    for prefix in ("This trigger node ", "This trigger "):
        if first.startswith(prefix):
            first = first[len(prefix):]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def describe(item: dict) -> str:
    text = item.get("node_description") or ""
    if text and not text.startswith("Use "):
        return _short(text)
    return _short(item.get("description") or text or item.get("node_name"))


def events(item: dict) -> list[dict]:
    config = item.get("config")
    event_type = config.get("event_type") if isinstance(config, dict) else None
    entries = event_type.get("items") if isinstance(event_type, dict) else None
    return [e for e in entries or [] if isinstance(e, dict) and e.get("event_name")]


def outputs(item: dict, with_types: bool) -> str:
    if "outputs" in OVERLAY.get(item["node_id"], {}):
        return "= form[].name"
    props = (item.get("output_schema") or {}).get("properties")
    if not props:
        return "none"
    if not with_types:
        return ",".join(props)
    return ",".join(f"{name}:{(spec or {}).get('type', '?')}" if isinstance(spec, dict) else name
                    for name, spec in props.items())


def _field_line(name: str, spec: dict, required: bool) -> str:
    parts = [name]
    if spec.get("type"):
        parts.append(str(spec["type"]))
    if spec.get("enum") is not None:
        parts.append("enum " + "|".join(json.dumps(v) for v in spec["enum"]))
    if "default" in spec:
        parts.append("default " + json.dumps(spec["default"]))
    items = spec.get("items")
    if isinstance(items, dict):
        if isinstance(items.get("properties"), dict):
            sub = [k + ("" if isinstance(s, dict) and s.get("required") is True else "?")
                   for k, s in items["properties"].items()]
            parts.append("items {" + ",".join(sub) + "}")
        elif items.get("enum") is not None:
            parts.append("items enum " + "|".join(json.dumps(v) for v in items["enum"]))
        elif items.get("type"):
            parts.append(f"items {items['type']}")
    parts.append("required" if required else "optional")
    return " ".join(parts)


def input_map_lines(item: dict) -> list[str]:
    nid = item["node_id"]
    if "input_map" in OVERLAY.get(nid, {}):
        return list(OVERLAY[nid]["input_map"])
    schema = item.get("arg_schema") or {}
    if not isinstance(schema, dict) or schema.get("type") == "array":
        return []
    lines: list[str] = []
    variants, key = [], None
    for branch in schema.get("oneOf") or []:
        props = branch.get("properties") or {}
        disc = [k for k, s in props.items() if isinstance(s, dict) and "const" in s]
        if not disc:
            continue
        key = disc[0]
        required = set(branch.get("required") or [])
        any_of = [r["required"][0] for r in branch.get("anyOf") or [] if r.get("required")]
        desc = []
        for name in (k for k in props if k != key):
            spec = props[name]
            items = spec.get("items") if isinstance(spec, dict) else None
            shape = ""
            if isinstance(items, dict) and isinstance(items.get("properties"), dict):
                shape = "[{" + ",".join(items["properties"]) + "}]"
            elif isinstance(items, dict) and items.get("type"):
                shape = f"[{items['type']}]"
            elif isinstance(spec, dict) and isinstance(spec.get("properties"), dict):
                shape = "{" + ",".join(spec["properties"]) + "}"
            desc.append(name + shape + ("" if name in required else "?"))
        tail = (" + " + ", ".join(desc)) if desc else ""
        if desc and any_of:
            tail += " (at least one of " + "/".join(any_of) + ")"
        variants.append(f"{props[key]['const']}{tail}")
    if key:
        lines.append(f"{key}: " + " | ".join(variants))
    required = set(schema.get("required") or [])
    for name, spec in (schema.get("properties") or {}).items():
        if isinstance(spec, dict):
            lines.append(_field_line(name, spec, name in required or spec.get("required") is True))
    for name, dep in (schema.get("dependencies") or {}).items():
        for branch in (dep or {}).get("oneOf") or []:
            cond = (branch.get("properties") or {}).get(name, {}).get("const")
            extra = [k for k in branch.get("required") or [] if k != name]
            if extra:
                lines.append(f"if {name}={json.dumps(cond)}: also {', '.join(extra)} required")
    return lines


def compiler_defaults(item: dict, cw) -> dict | None:
    if item["node_id"] in (cw.RSS_TRIGGER_NODE_ID, cw.SCHEDULER_TRIGGER_NODE_ID, cw.MANUAL_FORM_TRIGGER_NODE_ID):
        return None
    try:
        return cw._complete_input_map({}, item.get("arg_schema") or {})
    except ValueError:
        return None


def config_line(item: dict, cw) -> str:
    if item["node_id"] == cw.MEETING_TRIGGER_NODE_ID:
        pairs = ", ".join(f"{name}->{field}" for name, field in cw.MEETING_EVENT_CONFIG_FIELDS.items())
        return ('REQUIRED {"event_name":E,"event_config":{F:<number>}}; E->F: ' + pairs +
                " (time_offset = minutes relative to the event, negative = before; time = late/early threshold minutes)")
    found = events(item)
    if found:
        return f"omit (or {{\"event_name\":\"{found[0]['event_name']}\"}}, no event_config)"
    return "omit"


def render_list(cw) -> str:
    lines = [
        "# Phase-1 trigger index (derived from resources/phase1_node_catalog.json and the compiler)",
        "Pick trigger.node_id from this list only. Bind trigger data as {{trigger.<field>}} using a listed "
        "top-level output; {{trigger}} alone and nested paths are rejected (a voice_message/sms_message variable "
        "may bind one nested field listed by --node-id).",
        f"Non-trigger catalog items ({', '.join(other_items())}) are not trigger choices; DP steps come from "
        "kind guided_dp/full_dp, and the voice/SMS nodes from kind voice_message/sms_message.",
        "Per trigger: outputs, config, input_map (key type enum default required), and what the compiler fills "
        "when a key is omitted. A filled [] / false is a placeholder, not a choice.",
        "For one trigger's full argument schema run: trigger_lookup.py --node-id <id> [--event <name>]",
        "",
    ]
    blocks = []
    for item in triggers():
        nid = item["node_id"]
        found = [e["event_name"] for e in events(item)]
        head = f"## {nid} | {(item.get('node_name') or '').strip()} | {describe(item)}"
        body = []
        if found and nid != cw.MEETING_TRIGGER_NODE_ID:
            body.append(f"event: {found[0]}")
        body.append(f"outputs: {outputs(item, with_types=True)}")
        if "outputs" in OVERLAY.get(nid, {}):
            body.append(f"outputs note: {OVERLAY[nid]['outputs']}")
        body.append(f"config: {config_line(item, cw)}")
        im = input_map_lines(item)
        body.append("input_map: " + ("none" if not im else ""))
        body.extend(f"  - {line}" for line in im)
        defaults = compiler_defaults(item, cw)
        if defaults:
            body.append(f"compiler fills if omitted: {json.dumps(defaults, sort_keys=True)}")
        if "note" in OVERLAY.get(nid, {}):
            body.append(f"note: {OVERLAY[nid]['note']}")
        blocks.append((head, body))
    i = 0
    while i < len(blocks):
        j = i + 1
        while j < len(blocks) and blocks[j][1] == blocks[i][1]:
            j += 1
        lines.extend(head for head, _ in blocks[i:j])
        lines.extend(blocks[i][1])
        lines.append("")
        i = j
    return "\n".join(lines).rstrip() + "\n"


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in ("$schema", "examples", "x-ui", "title")}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def detail(item: dict, event: str | None, cw) -> dict:
    nid = item["node_id"]
    props = (item.get("output_schema") or {}).get("properties") or {}
    nested = {name: sorted((spec.get("properties") or {}).keys())
              for name, spec in props.items() if isinstance(spec, dict) and spec.get("properties")}
    found = events(item)
    if nid == cw.MEETING_TRIGGER_NODE_ID:
        names = [event] if event else list(cw.MEETING_EVENT_CONFIG_FIELDS)
        unknown = [n for n in names if n not in cw.MEETING_EVENT_CONFIG_FIELDS]
        if unknown:
            raise ValueError(f"unknown meeting event {unknown[0]!r}; choose one of {sorted(cw.MEETING_EVENT_CONFIG_FIELDS)}")
        config = {n: {"event_name": n, "event_config": {cw.MEETING_EVENT_CONFIG_FIELDS[n]: "<number>"}} for n in names}
        if event:
            config = config[event]
    elif found:
        config = {"event_name": found[0]["event_name"]}
    else:
        config = None
    result = {
        "node_id": nid,
        "node_name": (item.get("node_name") or "").strip(),
        "description": describe(item),
        "planir_config": config,
        "input_map_summary": input_map_lines(item),
        "input_map_schema": None if "input_map" in OVERLAY.get(nid, {}) else _strip(item.get("arg_schema") or {}),
        "compiler_fills_if_omitted": compiler_defaults(item, cw),
        "bindable_outputs": {name: (spec or {}).get("type", "?") for name, spec in props.items()} or None,
        "nested_output_fields": nested or None,
        "nested_note": "nested fields describe the payload; bind only {{trigger.<top-level output>}}, except a voice_message/sms_message variable, which may bind one listed nested field ({{trigger.<output>.<field>}})" if nested else None,
    }
    if "outputs" in OVERLAY.get(nid, {}):
        result["outputs_note"] = OVERLAY[nid]["outputs"]
    if "note" in OVERLAY.get(nid, {}):
        result["note"] = OVERLAY[nid]["note"]
    return {k: v for k, v in result.items() if v is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--node-id")
    parser.add_argument("--event", help="meeting event name, for zm.meeting.meeting.meeting_event")
    args = parser.parse_args()
    cw = load_compiler()
    if args.list:
        sys.stdout.write(render_list(cw))
        return 0
    by_id = {item["node_id"]: item for item in triggers()}
    if args.node_id not in by_id:
        nearest = difflib.get_close_matches(args.node_id, list(by_id), n=3, cutoff=0.4)
        print(json.dumps({"not_found": True, "node_id": args.node_id, "nearest": nearest}))
        return 1
    try:
        print(json.dumps(detail(by_id[args.node_id], args.event, cw), ensure_ascii=False, separators=(",", ":")))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
