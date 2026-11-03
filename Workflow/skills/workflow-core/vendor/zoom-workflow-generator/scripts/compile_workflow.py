"""Deterministic compiler: PlanIR -> Zoom Workflow FlowData for the DP-first planner_v3 skill.

The model authors a compact PlanIR (never raw FlowData); this compiler owns all node shape,
serialization, app scope, discovery flags, edge wiring, and structural validation. The default
palette emits Trigger, Condition, guided DP, full DP, and Custom Script. A creation call the caller
allows may additionally emit one or more HTML Render nodes, each optionally followed by one terminal
DP that delivers its declared URL. The compiler statically validates model-authored Python and HTML but
never executes or renders either artifact.

Node payloads match the runtime renderer contract:
- ``input_map.tools`` = grouped ``AgentTool`` objects (``app_key``/``app_name``/``source``/
  ``description``/``tool_details``). Phase 1 pins at APP level (``tool_details: []`` = whole app) +
  run-time tool discovery -- the proven shipped ``_DR_TOOLS`` shape; it needs no per-tool catalog
  hydration and carries no bare string ids.
- ``input_map.skills`` = ONE dynamic ``SkillItem`` with a non-empty ``description`` (the
  editor requires name+description+skill_type), inline ``md_content`` (the copied
  capsule body), and EXACT ``required_tools`` (a non-empty list overrides registry metadata).
- ``config`` persists the discovery flags + ``selected_apps`` EXPLICITLY (defaults are True and are
  not a stable serialized contract; an empty ``selected_apps`` blocks all tools in workflow mode).

Only ``print`` structural status JSON -- no logger, no customer content (safe-logging).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import uuid

try:
    from itertools import pairwise
except ImportError:
    from itertools import tee

    def pairwise(iterable):
        first, second = tee(iterable)
        next(second, None)
        return zip(first, second)


SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOG = SKILL_DIR / "resources" / "phase1_node_catalog.json"
CAPSULE_CATALOG = SKILL_DIR / "resources" / "dp_capsule_catalog.json"
APP_INDEX = SKILL_DIR / "resources" / "app_scope_index.json"

DR_NODE_ID = "zm.aic.agent.deep_reasoning"
CONDITION_NODE_ID = "zm.system.operators.condition"
CODE_NODE_ID = "zm.system.operators.code"
HTML_NODE_ID = "zm.system.operators.html"
VOICE_NODE_ID = "zm.asyncnotify.mobile.voice_node"
SMS_NODE_ID = "zm.asyncnotify.mobile.sms_node"
_MOBILE_NOTIFY_CHANNELS = {
    "voice_message": (VOICE_NODE_ID, "Send voice message"),
    "sms_message": (SMS_NODE_ID, "Send SMS message"),
}
_MOBILE_NOTIFY_TEMPLATE_ID = "tpl_d7c2a5e9f4b1a863"
_MOBILE_NOTIFY_TEMPLATES = {
    "tpl_d7c2a5e9f4b1a863": ("Workflow Success Reminder", ("workflow.name", "workflow.url")),
    "tpl_3e8f1a6b9c2d4f70": ("Scheduled Reminder", ("workflow.name", "workflow.url")),
    "tpl_8f3a9c2d1b7e4a6f": (
        "Meeting Start Reminder",
        ("user.displayName", "meeting.title", "meeting.start_time", "meeting.url"),
    ),
    "tpl_c4d91e7a2b5f8a03": (
        "Meeting End Reminder",
        ("user.displayName", "meeting.title", "meeting.end_time", "Summary or Message URL"),
    ),
}
_MOBILE_NOTIFY_CREATOR_BINDINGS = {"ROOT.sysWorkflowCreator.display_name"}
_MOBILE_NOTIFY_PHONE_RE = re.compile(r"^[+]?[0-9]{1,}$")
MEETING_TRIGGER_NODE_ID = "zm.meeting.meeting.meeting_event"
MANUAL_FORM_TRIGGER_NODE_ID = "zm.system.manual.trigger_form"
RSS_TRIGGER_NODE_ID = "zm.system.rss.feed"
SCHEDULER_TRIGGER_NODE_ID = "zm.system.scheduler.trigger.scheduler"
RSS_TRIGGER_APP_KEY = "zm_rss"
RSS_DEFAULT_POLL_INTERVAL_MINUTES = 15
RSS_TRIGGER_PLAN_INPUT_FIELDS = frozenset({"feed_urls", "poll_interval_minutes"})
MEETING_EVENT_CONFIG_FIELDS = {
    "meeting.start": "time_offset",
    "meeting.end": "time_offset",
    "meeting.participant_joined_late": "time",
    "meeting.participant_left_early": "time",
    "meeting.summary_created": "time_offset",
}
_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_OUTPUT_NAME_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_SCHEMA_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TEMPLATE_PAIR_RE = re.compile(r"\{\{([^}]+)\}\}")
_REFERENCE_PATH_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)\.([A-Za-z_][A-Za-z0-9_.\[\]-]*)\Z")
_HTML_SLOT_REFERENCE_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_HTML_BARE_SLOT_REFERENCE_RE = re.compile(r"\$([A-Za-z_]\w*)")
_HTML_ANY_BRACED_EXPRESSION_RE = re.compile(r"\$\{([^}]*)\}")
_HTML_UNSUPPORTED_DIRECTIVE_RE = re.compile(
    r"#(?:foreach|if|elseif|else|end|set|macro|parse|include|break|stop)\b",
    re.IGNORECASE,
)
_CODE_INPUT_GET_RE = re.compile(r"""input_data\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]""")
_CODE_INPUT_SUBSCRIPT_RE = re.compile(r"""input_data\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]""")
_CODE_INPUT_VALUES_RE = re.compile(r"input_data\.values\s*\(")
_ALLOWED_FIELD_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "null", "unknown"}
)
_ALLOWED_CODE_IMPORTS = frozenset(
    {
        "collections",
        "datetime",
        "decimal",
        "functools",
        "html",
        "itertools",
        "json",
        "math",
        "operator",
        "pathlib",
        "re",
        "statistics",
        "typing",
    }
)
_FORBIDDEN_CODE_CALLS = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "getattr",
        "globals",
        "input",
        "locals",
        "open",
        "os.system",
        "setattr",
        "subprocess.run",
        "vars",
    }
)
_HTML_ALLOWED_SLOT_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "null", "unknown"}
)
_HTML_DELIVERY_URL_PROMPT_GUARD = """## HTML artifact URL normalization (required)
Before sending or sharing the bound HTML URL, normalize only its render-route prefix:
- replace `/aic#aic/render/` with `/aic/?embedded=true#/aic/render/`;
- replace `/#aic/render/` with `/aic/?embedded=true#/aic/render/`;
- replace `/#/aic/render/` with `/aic/?embedded=true#/aic/render/`.
Preserve the URL scheme, authority, and artifact token. Deliver only the normalized URL, and stop
without sending unless the result contains `/aic/?embedded=true#/aic/render/`."""
_DELIVERY_ACTIONS = frozenset({"draft", "send"})
_DRAFT_SEND_CONFLICT_RE = re.compile(
    r"(?:\bgmail[_ .-]*send(?:[_ .-]*email)?\b|\bsend(?:ing|s|ed|t)?\b)",
    re.IGNORECASE,
)
_SEND_DRAFT_CONFLICT_RE = re.compile(
    r"(?:\bgmail[_ .-]*create[_ .-]*draft\b|\bdraft(?:ing|s|ed)?\b|\bnot\s+send\s+yet\b)",
    re.IGNORECASE,
)
_HTML_FORBIDDEN_TAGS = frozenset({"iframe", "object", "embed", "frame", "frameset", "base", "form"})
_HTML_FORBIDDEN_APIS = (
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "eventsource",
    "sendbeacon",
    "broadcastchannel",
    "messagechannel",
    "postmessage",
    "localstorage",
    "sessionstorage",
    "indexeddb",
    "document.cookie",
    "window.parent",
    "window.top",
    "window.opener",
    "sharedworker",
    "new worker(",
)
_MAX_HTML_TEMPLATE_BYTES = 200_000
_REQUIRED_CODE_RELIABILITY_OUTPUTS = {
    "code_succeeded": "boolean",
    "error_message": "string",
}


def _html_slot_is_json_payload(template: str, slot_name: str) -> bool:
    if "json.parse" not in template.lower():
        return False
    escaped_name = re.escape(slot_name)
    slot_reference = rf"(?:\$\{{{escaped_name}\}}|\${escaped_name}\b)"
    return (
        re.search(
            rf"<script\b(?=[^>]*\btype\s*=\s*['\"]application/json['\"])[^>]*>"
            rf".*?{slot_reference}.*?</script\s*>",
            template,
            re.IGNORECASE | re.DOTALL,
        )
        is not None
    )


_MAX_COMPILED_WORKFLOW_BYTES = 175_000
_MAX_MULTI_CAPSULE_BODY_BYTES = 65_000
_INSTRUCTION_CONTRACT_VERSION = 1
_INSTRUCTION_CONTRACT_FIELDS = frozenset(
    {
        "version",
        "role",
        "objective",
        "inputs",
        "procedure",
        "outputs",
        "missing_data_policy",
        "evidence_policy",
        "tool_policy",
        "side_effect_policy",
        "success_criteria",
    }
)
_INSTRUCTION_INPUT_FIELDS = frozenset({"name", "source", "purpose"})

_EXECUTION_RECEIPT_LINES = (
    "## Execution receipt",
    "- Begin the `response` value with a compact execution receipt of at most 1000 characters, "
    "before any report, message body, analysis, or other long-form content.",
    "- Start the receipt with `Outcome: SUCCESS`, `Outcome: PARTIAL`, `Outcome: NO_ACTION`, "
    "or `Outcome: FAILED`, matching the observed run result.",
    "- Add `Reads:` with the provider/source plus the concrete record identifiers, titles, "
    "queries, or result counts actually observed and used; write `Reads: NONE` when no read ran.",
    "- Add `Writes:` with one compact entry per attempted side effect: provider, operation, "
    "resolved target or recipient, provider-confirmed status, and returned identifier or URL when "
    "the tool supplies one. If no write ran, state `Writes: NONE` and the reason.",
    "- Add `Checks:` with every core requested section, field, constraint, and required sink marked "
    "`OK` or `MISSING` from observed evidence. Keep it terse, but never omit a failed core check to "
    "fit the receipt; for a long artifact, this checklist is the bounded proof of its contents.",
    "- Never claim success from intent or generated content alone, never invent receipt evidence, "
    "and never defer the only business-outcome evidence until after long-form content.",
)

_FULL_DP_PROVIDER_SAFEGUARDS = {
    "zm_jira": (
        "Before any Jira issue create or bulk-create call, resolve the target project and read "
        "that project's creatable issue types with Jira project metadata tools.",
        "Pass only the exact case-sensitive issue-type name returned for that project. Never "
        "guess an issue type from examples, defaults, or a Bug/Story/Task classification alone.",
        "If the requested or classified issue type is unavailable, ask the user to choose from "
        "the returned types or stop without writing; do not substitute another type silently.",
    ),
}

_CONDITION_OPERATORS = frozenset(
    {
        "eq",
        "neq",
        "gt",
        "lt",
        "gte",
        "lte",
        "contains",
        "notContains",
        "isIn",
        "isNotIn",
        "startWith",
        "notStartWith",
        "endWith",
        "notEndWith",
        "isEmpty",
        "isNotEmpty",
        "isTrue",
        "isFalse",
    }
)
_CONDITION_OPERATOR_ALIASES = {
    "==": "eq",
    "equal": "eq",
    "equals": "eq",
    "!=": "neq",
    "notequal": "neq",
    "notequals": "neq",
    "greaterthan": "gt",
    "lessthan": "lt",
    "greaterthanorequal": "gte",
    "lessthanorequal": "lte",
}
_CONDITION_OPERATOR_BY_LOWER = {operator.lower(): operator for operator in _CONDITION_OPERATORS}
_BOOLEAN_CONDITION_OPERATORS = frozenset({"isTrue", "isFalse"})
_UNARY_CONDITION_OPERATORS = frozenset({"isTrue", "isFalse", "isEmpty", "isNotEmpty"})
_NUMERIC_CONDITION_OPERATORS = frozenset({"gt", "lt", "gte", "lte"})


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_strings(child)


def _normalized_phrase(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _required_instruction_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"instruction_contract.{field_name} must be a non-empty string")
    return value.strip()


def _required_instruction_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"instruction_contract.{field_name} must be a non-empty array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"instruction_contract.{field_name} must contain non-empty strings")
    return [item.strip() for item in value]


def _render_typed_output_requirements(outputs: list[dict]) -> list[str]:
    rendered: list[str] = []
    for output in outputs:
        name = output["name"]
        output_type = output.get("type", "string")
        description = output.get("description", "")
        rendered.append(f"- `{name}` ({output_type}): {description}")
    return rendered


def _render_full_dp_provider_safeguards(app_scope: list[str]) -> list[str]:
    safeguards = [
        safeguard
        for app_key in app_scope
        for safeguard in _FULL_DP_PROVIDER_SAFEGUARDS.get(app_key, ())
    ]
    if not safeguards:
        return []
    return ["## Provider write safeguards", *(f"- {item}" for item in safeguards), ""]


def _render_capsule_task_prompt_guards(capsule: dict) -> list[str]:
    raw_guards = capsule.get("task_prompt_guards")
    if raw_guards in (None, []):
        return []
    if not isinstance(raw_guards, list) or any(
        not isinstance(guard, str) or not guard.strip() for guard in raw_guards
    ):
        raise ValueError("guided DP capsule task_prompt_guards must be non-empty strings")
    return [
        "",
        "## Mandatory capsule execution guardrails",
        *(f"- {guard.strip()}" for guard in raw_guards),
    ]


def _delivery_action(step: dict) -> str | None:
    action = step.get("delivery_action")
    if action is None:
        return None
    if not isinstance(action, str) or action.strip().lower() not in _DELIVERY_ACTIONS:
        raise ValueError("delivery_action must be either 'draft' or 'send'")
    return action.strip().lower()


_NEGATED_DELIVERY_RE = re.compile(
    r"\b(?:never|not|no|don't|do\s+not|without|instead\s+of)\s+(?:\w+\s+){0,3}?(?:send|draft)\w*\b",
    re.IGNORECASE,
)


def _authored_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _authored_strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _authored_strings(item)]
    return []


def _validate_delivery_action(step: dict, task_prompt: str) -> str | None:
    action = _delivery_action(step)
    authored = "\n".join(_authored_strings([step.get("intent"), step.get("instruction_contract")]))
    authored = _NEGATED_DELIVERY_RE.sub(" ", authored)
    if action == "draft" and _DRAFT_SEND_CONFLICT_RE.search(authored):
        raise ValueError("delivery_action draft conflicts with send instructions")
    if action == "send" and _SEND_DRAFT_CONFLICT_RE.search(authored):
        raise ValueError("delivery_action send conflicts with draft instructions")
    return action


def _render_task_prompt(
    step: dict,
    outputs: list[dict],
    *,
    provider_safeguards: list[str] | None = None,
) -> str:
    raw_intent = step.get("intent")
    if not isinstance(raw_intent, str) or not raw_intent.strip():
        raise ValueError("DP step intent must be a non-empty string")
    intent = raw_intent.strip()
    action = _delivery_action(step)
    raw_contract = step.get("instruction_contract")
    if raw_contract is None:
        raise ValueError("every DP step requires instruction_contract.version 1")
    if not isinstance(raw_contract, dict):
        raise ValueError("instruction_contract must be an object")
    unknown_fields = set(raw_contract) - _INSTRUCTION_CONTRACT_FIELDS
    if unknown_fields:
        raise ValueError("instruction_contract contains unsupported fields")
    version = raw_contract.get("version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != _INSTRUCTION_CONTRACT_VERSION
    ):
        raise ValueError(f"instruction_contract.version must be {_INSTRUCTION_CONTRACT_VERSION}")

    role = _required_instruction_text(raw_contract.get("role"), "role")
    objective = _required_instruction_text(raw_contract.get("objective"), "objective")
    procedure = _required_instruction_list(raw_contract.get("procedure"), "procedure")
    output_requirements = _required_instruction_list(raw_contract.get("outputs"), "outputs")
    success_criteria = _required_instruction_list(
        raw_contract.get("success_criteria"), "success_criteria"
    )
    missing_data_policy = _required_instruction_text(
        raw_contract.get("missing_data_policy"), "missing_data_policy"
    )
    evidence_policy = _required_instruction_text(
        raw_contract.get("evidence_policy"), "evidence_policy"
    )
    tool_policy = _required_instruction_text(raw_contract.get("tool_policy"), "tool_policy")
    side_effect_policy = _required_instruction_text(
        raw_contract.get("side_effect_policy"), "side_effect_policy"
    )

    raw_inputs = raw_contract.get("inputs")
    if not isinstance(raw_inputs, list):
        raise ValueError("instruction_contract.inputs must be an array")
    input_names: set[str] = set()
    rendered_inputs: list[str] = []
    for raw_input in raw_inputs:
        if not isinstance(raw_input, dict):
            raise ValueError("instruction_contract.inputs entries must be objects")
        if set(raw_input) - _INSTRUCTION_INPUT_FIELDS:
            raise ValueError("instruction_contract.inputs entries contain unsupported fields")
        name = _required_instruction_text(raw_input.get("name"), "inputs[].name")
        if name in input_names:
            raise ValueError("instruction_contract input names must be unique")
        input_names.add(name)
        source = _required_instruction_text(raw_input.get("source"), "inputs[].source")
        purpose = _required_instruction_text(raw_input.get("purpose"), "inputs[].purpose")
        rendered_inputs.append(f"- **{name}** from `{source}` — {purpose}")
    if not rendered_inputs:
        rendered_inputs.append(
            "- No upstream payload; use only the current workflow-run context and the authorized capabilities selected for this step."
        )

    numbered_procedure = [f"{index}. {item}" for index, item in enumerate(procedure, 1)]
    rendered_outputs = [f"- {item}" for item in output_requirements]
    rendered_success = [f"- {item}" for item in success_criteria]
    task_prompt = "\n".join(
        [
            "# Execution contract",
            "",
            "## Role",
            role,
            "",
            "## Objective",
            objective,
            *(["", "## Requested delivery action", action] if action else []),
            "",
            "## Inputs",
            *rendered_inputs,
            "",
            "## Procedure",
            *numbered_procedure,
            "",
            "## Output requirements",
            *rendered_outputs,
            "",
            "## Typed outputs",
            *_render_typed_output_requirements(outputs),
            "",
            "## Missing-data policy",
            missing_data_policy,
            "",
            "## Evidence policy",
            evidence_policy,
            "",
            "## Tool policy",
            tool_policy,
            "",
            "## Side-effect policy",
            side_effect_policy,
            "",
            "## Success criteria",
            *rendered_success,
            "",
            *(provider_safeguards or []),
            *_EXECUTION_RECEIPT_LINES,
        ]
    )
    _validate_delivery_action(step, task_prompt)
    return task_prompt


def _has_contradictory_side_effect_policy(value: str) -> bool:
    normalized = " ".join(value.lower().split())
    success_gate = re.search(
        r"\bonly (?:if|after)\b.{0,220}?\b(?:confirm(?:s|ed)?|success(?:ful(?:ly)?)?|"
        r"succeed(?:s|ed)?)\b.{0,100}?\b(send|post|message|create|update|write)\b",
        normalized,
    )
    failure_continue = re.search(
        r"\bif\b.{0,180}?\b(?:fail|fails|failed|failure)\b.{0,100}?\bstill\b.{0,40}?"
        r"\b(send|post|message|create|update|write)\b(?P<failure_action>.{0,100})",
        normalized,
    )
    if not (
        success_gate and failure_continue and success_gate.group(1) == failure_continue.group(1)
    ):
        return False

    failure_action = failure_continue.group("failure_action")
    distinct_failure_notice = re.search(
        r"^\s*(?:a|an|the)?\s*(?:(?:failure|error|warning)\s+)?"
        r"(?:notification|alert|message)\b.{0,60}\b(?:fail(?:s|ed|ure)?|error|warning)\b"
        r"|^\s*(?:a|an|the)?\s*(?:failure|error|warning)\s+"
        r"(?:notification|alert|message)\b",
        failure_action,
    )
    return distinct_failure_notice is None


def _normalize_condition_operator(operator: str) -> str:
    stripped = operator.strip()
    normalized = _CONDITION_OPERATOR_BY_LOWER.get(stripped.lower())
    if normalized:
        return normalized
    alias_key = "".join(character for character in stripped.lower() if character.isalnum())
    normalized = _CONDITION_OPERATOR_ALIASES.get(stripped) or _CONDITION_OPERATOR_ALIASES.get(
        alias_key
    )
    if normalized:
        return normalized
    raise ValueError("condition entry uses an unsupported operator")


def _default_for(field_schema: dict):
    fs = field_schema if isinstance(field_schema, dict) else {}
    if "default" in fs:
        return fs["default"]
    if "const" in fs:
        return fs["const"]
    enum = fs.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    field_type = str(fs.get("type") or "string").lower()
    if field_type == "array":
        return []
    if field_type == "object":
        return {}
    if field_type in {"integer", "number"}:
        minimum = fs.get("minimum")
        return minimum if isinstance(minimum, (int, float)) else 0
    if field_type == "boolean":
        return False
    return ""


def _direct_required(schema: dict) -> list[str]:
    req = schema.get("required") if isinstance(schema, dict) else None
    return [str(n) for n in req if isinstance(n, str)] if isinstance(req, list) else []


def _branch_satisfied(value: dict, schema: dict) -> bool:
    if not isinstance(schema, dict):
        return True
    if not set(_direct_required(schema)) <= set(value):
        return False
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, field_schema in properties.items():
            if name not in value or not isinstance(field_schema, dict):
                continue
            if "const" in field_schema and value[name] != field_schema["const"]:
                return False
            enum = field_schema.get("enum")
            if isinstance(enum, list) and enum and value[name] not in enum:
                return False
    for branch in schema.get("allOf") or []:
        if isinstance(branch, dict) and not _branch_satisfied(value, branch):
            return False
    for keyword in ("oneOf", "anyOf"):
        alts = [b for b in (schema.get(keyword) or []) if isinstance(b, dict)]
        if alts and not any(_branch_satisfied(value, b) for b in alts):
            return False
    return True


def _satisfy(value: dict, schema: dict) -> None:
    if not isinstance(schema, dict):
        return
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = set(_direct_required(schema))
    required.update(
        str(n) for n, s in props.items() if isinstance(s, dict) and s.get("required") is True
    )
    for name in required:
        if name not in value:
            value[name] = _default_for(props.get(name) or {})
    for branch in schema.get("allOf") or []:
        if isinstance(branch, dict):
            _satisfy(value, branch)
    for keyword in ("oneOf", "anyOf"):
        alts = [b for b in (schema.get(keyword) or []) if isinstance(b, dict)]
        if alts and not any(_branch_satisfied(value, b) for b in alts):
            best = min(
                alts,
                key=lambda b: (len(_direct_required(b)), len(b.get("properties") or {})),
            )
            _satisfy(value, best)


def _complete_input_map(input_map: dict, arg_schema: dict) -> dict:
    if not isinstance(arg_schema, dict):
        return dict(input_map)
    completed = dict(input_map)
    _satisfy(completed, arg_schema)
    if not _branch_satisfied(completed, arg_schema):
        raise ValueError("trigger input_map conflicts with its schema")
    return completed


def _gen_ref(prefix: str, taken: set[str]) -> str:
    i = 1
    while f"{prefix}{i}" in taken:
        i += 1
    ref = f"{prefix}{i}"
    taken.add(ref)
    return ref


def _agent_tools(app_scope: list[str], app_index: dict) -> list[dict]:
    apps = app_index.get("apps", {})
    out = []
    for key in app_scope:
        meta = apps.get(key)
        if not meta:
            raise ValueError("DP app scope contains an unknown app key")
        out.append(
            {
                "app_key": meta["app_key"],
                "app_name": meta["app_name"],
                "source": meta["source"],
                "description": meta.get("app_name", ""),
                "authorized": True,
                "tool_details": [],
            }
        )
    return out


def _requested_apps(
    step: dict,
    app_index: dict,
    *,
    allow_empty: bool,
) -> list[str]:
    requested = step.get("requested_apps")
    if not isinstance(requested, list) or (not allow_empty and not requested):
        requirement = "an array" if allow_empty else "at least one app"
        raise ValueError(f"DP requested_apps must contain {requirement}")
    if any(not isinstance(key, str) or not key for key in requested):
        raise ValueError("DP requested_apps must contain non-empty strings")
    if len(set(requested)) != len(requested):
        raise ValueError("DP requested_apps must be unique")
    known_apps = app_index.get("apps")
    if not isinstance(known_apps, dict) or any(key not in known_apps for key in requested):
        raise ValueError("DP requested_apps contains an unknown app key")
    return list(requested)


def _dr_outputs(
    typed_outputs: list[dict] | None,
    *,
    require_descriptions: bool = False,
) -> tuple[list[dict], dict]:
    if typed_outputs is not None and not isinstance(typed_outputs, list):
        raise ValueError("DP outputs must be an array")
    outs: list[dict] = []
    seen: set[str] = set()
    for raw in typed_outputs or []:
        if not isinstance(raw, dict):
            raise ValueError("DP output entry must be an object")
        name = raw.get("name")
        if not isinstance(name, str) or not _OUTPUT_NAME_RE.fullmatch(name):
            raise ValueError("DP output name must be a valid identifier")
        if name in seen:
            raise ValueError("DP output names must be unique")
        seen.add(name)
        output_type = raw.get("type", "string")
        if not isinstance(output_type, str) or not output_type:
            raise ValueError("DP output type must be a non-empty string")
        description = raw.get("description", "")
        if not isinstance(description, str):
            raise ValueError("DP output description must be a string")
        if require_descriptions and not description.strip():
            raise ValueError(
                "DP output description must be non-empty when instruction_contract is present"
            )
        outs.append(
            {
                "name": name,
                "type": output_type,
                "description": description,
                "required": False,
            }
        )
    if not any(o.get("name") == "response" for o in outs):
        outs.insert(
            0,
            {
                "name": "response",
                "type": "string",
                "description": (
                    "Plain-language execution result, including observed side-effect status "
                    "when applicable"
                ),
                "required": False,
            },
        )
    output_schema = {
        "type": "object",
        "properties": {
            o["name"]: {"type": o.get("type", "string"), "description": o.get("description", "")}
            for o in outs
        },
    }
    return outs, output_schema


def _merge_capsule_outputs(capsule_outputs: object, plan_outputs: object) -> list[dict]:
    if not isinstance(capsule_outputs, list):
        raise ValueError("guided DP capsule typed_outputs are invalid")
    if plan_outputs is None:
        return [dict(output) for output in capsule_outputs]
    if not isinstance(plan_outputs, list):
        raise ValueError("DP outputs must be an array")

    required_by_name: dict[str, dict] = {}
    for output in capsule_outputs:
        if not isinstance(output, dict) or not isinstance(output.get("name"), str):
            raise ValueError("guided DP capsule typed_outputs are invalid")
        required_by_name[output["name"]] = output

    supplied_by_name: dict[str, dict] = {}
    for output in plan_outputs:
        if not isinstance(output, dict) or not isinstance(output.get("name"), str):
            raise ValueError("DP output entry must be an object with a name")
        name = output["name"]
        if name in supplied_by_name:
            raise ValueError("DP output names must be unique")
        supplied_by_name[name] = output
        required = required_by_name.get(name)
        if required and output.get("type", "string") != required.get("type", "string"):
            raise ValueError("guided DP cannot change a required capsule output type")

    merged = [dict(output) for output in capsule_outputs]
    merged.extend(
        dict(output) for output in plan_outputs if output.get("name") not in required_by_name
    )
    return merged


def _node_scaffold(node_id: str, ref: str, node_type: str, name: str) -> dict:
    return {
        "node_id": node_id,
        "reference_id": ref,
        "node_type": node_type,
        "node_name": name,
        "node_alias": "",
        "node_desc": "",
        "input_map": {},
        "config": {},
        "output_schema": {},
        "expanded": False,
        "children": {"nodes": [], "edges": []},
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _catches_exception(node: ast.AST) -> bool:
    return any(
        isinstance(candidate, ast.Try)
        and any(
            isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
            for handler in candidate.handlers
        )
        for candidate in ast.walk(node)
    )


def _main_guard(tree: ast.Module) -> ast.If | None:
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if (
            isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return node
    return None


def _has_safe_request_path_assignment(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not isinstance(target, ast.Name) or target.id != "request_path":
            continue
        if (
            not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Attribute)
            or value.func.attr != "with_name"
        ):
            continue
        receiver = value.func.value
        if (
            isinstance(receiver, ast.Call)
            and _call_name(receiver.func) == "Path"
            and len(receiver.args) == 1
            and isinstance(receiver.args[0], ast.Name)
            and receiver.args[0].id == "__file__"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Constant)
            and value.args[0].value == "request.json"
        ):
            return True
    return False


def _validate_binding_source(source: object, *, label: str) -> str:
    if not isinstance(source, str):
        raise ValueError(f"{label} source must be a workflow binding string")
    match = _TEMPLATE_PAIR_RE.fullmatch(source.strip())
    reference = match.group(1).strip().partition("|")[0].strip() if match else ""
    reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
    if reference_match is None:
        raise ValueError(f"{label} source must bind one declared node output field")
    _, field_path = reference_match.groups()
    if "." in field_path or "[" in field_path or "]" in field_path:
        raise ValueError(f"{label} source must bind a top-level output field")
    return source.strip()


def _normalize_schema_fields(
    raw_fields: object,
    *,
    label: str,
    require_non_empty: bool,
) -> list[dict]:
    if not isinstance(raw_fields, list) or (require_non_empty and not raw_fields):
        requirement = "a non-empty array" if require_non_empty else "an array"
        raise ValueError(f"{label} must be {requirement}")
    fields: list[dict] = []
    names: set[str] = set()
    for raw in raw_fields:
        if not isinstance(raw, dict):
            raise ValueError(f"{label} entries must be objects")
        name = raw.get("name")
        field_type = raw.get("type")
        description = raw.get("description")
        required = raw.get("required", False)
        if not isinstance(name, str) or not _SCHEMA_FIELD_NAME_RE.fullmatch(name):
            raise ValueError(f"{label} field names must be valid Python identifiers")
        if name in names:
            raise ValueError(f"{label} field names must be unique")
        if not isinstance(field_type, str) or field_type not in _ALLOWED_FIELD_TYPES:
            raise ValueError(f"{label} field types are unsupported")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{label} field descriptions must be non-empty")
        if not isinstance(required, bool):
            raise ValueError(f"{label} required values must be booleans")
        names.add(name)
        fields.append(
            {
                "name": name,
                "type": field_type,
                "description": description.strip(),
                "required": required,
            }
        )
    return fields


def _validate_python_artifact(code: object, input_names: set[str]) -> str:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("custom_script code must be a non-empty string")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(
            f"custom_script code has a Python syntax error at line {exc.lineno}: {exc.msg}"
        ) from exc

    run_node_defs = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_node"
    ]
    if len(run_node_defs) != 1:
        raise ValueError(
            "custom_script code must define run_node(input_data, context) exactly once"
        )
    run_node = run_node_defs[0]
    positional_args = [*run_node.args.posonlyargs, *run_node.args.args]
    if (
        [argument.arg for argument in positional_args] != ["input_data", "context"]
        or run_node.args.vararg is not None
        or run_node.args.kwarg is not None
        or run_node.args.kwonlyargs
    ):
        raise ValueError("custom_script run_node must accept exactly input_data and context")
    if not _catches_exception(run_node):
        raise ValueError("custom_script run_node must catch Exception")
    main_guard = _main_guard(tree)
    if main_guard is None or not _catches_exception(main_guard):
        raise ValueError("custom_script launcher must catch Exception")

    unsafe: str | None = None
    has_runtime_envelope = False
    has_print = False
    has_json_dumps = False
    path_constructor_count = 0
    for syntax_node in ast.walk(tree):
        if isinstance(syntax_node, ast.Import):
            roots = [alias.name.split(".", 1)[0] for alias in syntax_node.names]
            unsafe = next((root for root in roots if root not in _ALLOWED_CODE_IMPORTS), None)
        elif isinstance(syntax_node, ast.ImportFrom):
            module = syntax_node.module or ""
            root = module.split(".", 1)[0]
            if syntax_node.level or root not in _ALLOWED_CODE_IMPORTS:
                unsafe = ("." * syntax_node.level + module) or "<relative import>"
        elif isinstance(syntax_node, ast.Call):
            name = _call_name(syntax_node.func)
            root = name.split(".", 1)[0]
            if name == "Path":
                path_constructor_count += 1
            if name in _FORBIDDEN_CODE_CALLS or root in {
                "requests",
                "httpx",
                "socket",
                "subprocess",
            }:
                unsafe = name
            if name.endswith((".read_text", ".read_bytes")) and name not in {
                "request_path.read_text",
                "request_path.read_bytes",
            }:
                unsafe = name
            has_print = has_print or name == "print"
            has_json_dumps = has_json_dumps or name == "json.dumps"
        elif isinstance(syntax_node, ast.Attribute):
            if syntax_node.attr.startswith("__") or syntax_node.attr in {
                "write_text",
                "write_bytes",
                "unlink",
                "rename",
                "rmdir",
                "mkdir",
            }:
                unsafe = syntax_node.attr
        elif isinstance(syntax_node, ast.Dict):
            keys = {
                key.value
                for key in syntax_node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            has_runtime_envelope = has_runtime_envelope or {"success", "output"} <= keys
        if unsafe:
            break
    if unsafe:
        raise ValueError(f"custom_script code uses unsupported import or call '{unsafe}'")
    if path_constructor_count != 1 or not _has_safe_request_path_assignment(tree):
        raise ValueError("custom_script filesystem access must be limited to sibling request.json")

    referenced_inputs = set(_CODE_INPUT_GET_RE.findall(code))
    referenced_inputs.update(_CODE_INPUT_SUBSCRIPT_RE.findall(code))
    if referenced_inputs - input_names:
        raise ValueError("custom_script code references undeclared input fields")
    if _CODE_INPUT_VALUES_RE.search(code):
        raise ValueError("custom_script code must access named inputs, not input_data.values()")
    if not has_runtime_envelope:
        raise ValueError("custom_script code must return the {success, output} runtime envelope")
    literal_keys = {
        key.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    if not set(_REQUIRED_CODE_RELIABILITY_OUTPUTS) <= literal_keys:
        raise ValueError("custom_script code must emit reliability outputs")
    if "__main__" not in code or "request.json" not in code:
        raise ValueError("custom_script code must include the request.json launcher")
    if not has_print or not has_json_dumps:
        raise ValueError("custom_script launcher must print json.dumps(result)")
    return code


def _trigger_config_schema(cat: dict) -> dict:
    config_schema = cat.get("config_schema")
    if isinstance(config_schema, dict):
        return config_schema
    config = cat.get("config")
    if not isinstance(config, dict):
        return {}
    event_type = config.get("event_type")
    if not isinstance(event_type, dict) or not isinstance(event_type.get("items"), list):
        return {}
    return config


def _catalog_node_set_id(cat: dict) -> str | None:
    raw_node = cat.get("raw_node")
    raw_node = raw_node if isinstance(raw_node, dict) else {}
    node_set_id = (
        cat.get("node_set_id")
        or cat.get("nodeSetId")
        or raw_node.get("node_set_id")
        or raw_node.get("nodeSetId")
    )
    return node_set_id if isinstance(node_set_id, str) and node_set_id else None


def _validate_trigger_config(node_id: str, config: dict, cat: dict) -> None:
    if not config:
        if node_id == MEETING_TRIGGER_NODE_ID:
            raise ValueError("meeting trigger requires an explicit event config")
        return
    if (
        set(config) > {"event_name", "event_config"}
        or not isinstance(config.get("event_name"), str)
        or not isinstance(config.get("event_config", {}), dict)
    ):
        raise ValueError("trigger config must contain event_name and an event_config object")

    event_type = _trigger_config_schema(cat).get("event_type")
    items = event_type.get("items") if isinstance(event_type, dict) else None
    if not isinstance(items, list):
        raise ValueError("trigger config is not backed by the bundled catalog")
    matching = [
        item
        for item in items
        if isinstance(item, dict) and item.get("event_name") == config["event_name"]
    ]
    if node_id == MEETING_TRIGGER_NODE_ID and config["event_name"] == "meeting.summary_created":
        matching = [{"event_config": {"time_offset": {"type": "number"}}}]
    if not matching:
        raise ValueError("trigger event is not supported by the bundled catalog")

    event_config = config.get("event_config", {})
    declared_event_config = matching[0].get("event_config")
    if isinstance(declared_event_config, dict):
        if set(event_config) - declared_event_config.keys():
            raise ValueError("trigger event_config contains an unsupported field")
    elif event_config:
        raise ValueError("trigger event does not accept event_config fields")

    if node_id == MEETING_TRIGGER_NODE_ID:
        required_field = MEETING_EVENT_CONFIG_FIELDS.get(config["event_name"])
        if required_field is None or set(event_config) != {required_field}:
            raise ValueError("meeting trigger event_config is incomplete")
        value = event_config[required_field]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("meeting trigger event_config must be numeric")


def _form_output_schema(input_map: dict, catalog_schema: dict) -> dict:
    fields = input_map.get("form")
    if not isinstance(fields, list):
        return catalog_schema
    derived = {
        field["name"]: {
            "type": field.get("type") if isinstance(field.get("type"), str) else "string",
            "description": field.get("description") or f"Form field {field['name']}",
        }
        for field in fields
        if isinstance(field, dict) and isinstance(field.get("name"), str) and field["name"]
    }
    if not derived:
        return catalog_schema
    return {
        **catalog_schema,
        "type": catalog_schema.get("type") or "object",
        "properties": {**(catalog_schema.get("properties") or {}), **derived},
    }


def _rss_trigger_input_map(input_map: dict) -> dict:
    unknown_fields = set(input_map) - RSS_TRIGGER_PLAN_INPUT_FIELDS
    if unknown_fields:
        raise ValueError("RSS trigger input_map contains unsupported fields")

    raw_feed_urls = input_map.get("feed_urls")
    if not isinstance(raw_feed_urls, list) or not raw_feed_urls:
        raise ValueError("RSS trigger requires at least one feed URL")
    feed_urls: list[str] = []
    for raw_feed_url in raw_feed_urls:
        if not isinstance(raw_feed_url, str) or not raw_feed_url.strip():
            raise ValueError("RSS trigger feed URLs must be non-empty strings")
        feed_url = raw_feed_url.strip()
        if not feed_url.lower().startswith(("https://", "http://")):
            raise ValueError("RSS trigger feed URLs must use HTTP or HTTPS")
        feed_urls.append(feed_url)
    if len(set(feed_urls)) != len(feed_urls):
        raise ValueError("RSS trigger feed URLs must be unique")

    poll_interval_minutes = input_map.get(
        "poll_interval_minutes", RSS_DEFAULT_POLL_INTERVAL_MINUTES
    )
    if (
        not isinstance(poll_interval_minutes, int)
        or isinstance(poll_interval_minutes, bool)
        or not 1 <= poll_interval_minutes <= 1440
    ):
        raise ValueError("RSS trigger poll interval must be between 1 and 1440 minutes")

    return {
        "appKey": RSS_TRIGGER_APP_KEY,
        "inputValues": [
            {"actionId": "difftype", "type": "text_field", "value": 0},
            {"actionId": "username", "type": "text_field", "value": ""},
            {"actionId": "password", "type": "password_input", "value": ""},
            {"actionId": "fedUrl", "type": "text_field", "value": feed_urls},
            {
                "actionId": "timerValue",
                "type": "text_field",
                "value": poll_interval_minutes,
            },
        ],
    }


def _emit_trigger(trigger: dict, by_id: dict, taken: set[str]) -> dict:
    node_id = trigger.get("node_id")
    cat = by_id.get(node_id)
    if not cat or cat.get("node_type") != "trigger":
        raise ValueError("trigger node_id is not a supported Phase-1 trigger")
    ref = _gen_ref("trg", taken)
    node = _node_scaffold(node_id, ref, "trigger", cat.get("node_name") or "Trigger")
    config = trigger.get("config") or {}
    input_map = trigger.get("input_map") or {}
    if not isinstance(config, dict) or not isinstance(input_map, dict):
        raise ValueError("trigger config and input_map must be objects")
    _validate_trigger_config(node_id, config, cat)
    node["config"] = config
    node["output_schema"] = cat.get("output_schema") or {}
    node_set_id = _catalog_node_set_id(cat)
    if node_set_id is not None:
        node["node_set_id"] = node_set_id
    if node_id == RSS_TRIGGER_NODE_ID:
        node["input_map"] = _rss_trigger_input_map(input_map)
    else:
        node["input_map"] = _complete_input_map(input_map, cat.get("arg_schema") or {})
    if node_id == SCHEDULER_TRIGGER_NODE_ID:
        required_schedule_fields = {
            "startsOn",
            "frequency",
            "repeatLevel",
            "repeatEvery",
            "repeatOn",
            "monthlyOn",
            "endType",
            "endDate",
            "executedTimes",
            "timezone",
        }
        if not required_schedule_fields <= node["input_map"].keys() or not all(
            node["input_map"].get(name) not in (None, "")
            for name in ("startsOn", "repeatLevel", "timezone")
        ):
            raise ValueError("scheduled trigger requires a complete concrete schedule")
    if node_id == MANUAL_FORM_TRIGGER_NODE_ID:
        node["output_schema"] = _form_output_schema(node["input_map"], node["output_schema"])
    return node


def _emit_guided_dp(step: dict, capsule: dict, app_index: dict, taken: set[str]) -> dict:
    ref = _gen_ref("dp", taken)
    name = step.get("node_name") or capsule.get("skill_name") or "AI reasoning"
    node = _node_scaffold(DR_NODE_ID, ref, "deep_reasoning", name)
    app_scope = capsule.get("app_scope") or []
    requested_apps = _requested_apps(step, app_index, allow_empty=True)
    if not set(requested_apps) <= set(app_scope):
        raise ValueError("guided DP capsule app_scope does not cover requested_apps")
    normalized_intent = _normalized_phrase(step.get("intent", ""))
    for phrase in capsule.get("incompatible_intent_phrases") or []:
        normalized_phrase = _normalized_phrase(phrase) if isinstance(phrase, str) else ""
        if normalized_phrase and f" {normalized_phrase} " in f" {normalized_intent} ":
            raise ValueError(
                "guided DP capsule is incompatible with this intent; use a matching capsule "
                "or full_dp"
            )
    required_tools = list(capsule.get("required_tools") or [])
    effective_app_scope = list(app_scope) if required_tools else (requested_apps or list(app_scope))
    merged_outputs = _merge_capsule_outputs(capsule.get("typed_outputs"), step.get("outputs"))
    outs, output_schema = _dr_outputs(
        merged_outputs,
        require_descriptions=step.get("instruction_contract") is not None,
    )
    task_prompt = "\n".join(
        [
            _render_task_prompt(step, outs),
            *_render_capsule_task_prompt_guards(capsule),
        ]
    )
    if _has_contradictory_side_effect_policy(task_prompt):
        raise ValueError("guided DP instruction has contradictory side-effect policy")
    body = (SKILL_DIR / capsule["body_path"]).read_text()
    node["config"] = {
        "execution_mode": "workflow",
        "allow_auto_tool_discovery": True,
        "allow_auto_skill_discovery": False,
        "available_tools": required_tools,
        "selected_apps": effective_app_scope,
        "only_use_selected_apps": True,
    }
    node["input_map"] = {
        "task_prompt": task_prompt,
        "system_prompt": "",
        "max_steps": 20,
        "knowledge": {"web_urls": ""},
        "tools": _agent_tools(effective_app_scope, app_index),
        "skills": [
            {
                "name": capsule["capsule_id"],
                "description": capsule.get("when_to_use") or capsule["capsule_id"],
                "skill_type": "dynamic",
                "md_content": body,
                "required_tools": required_tools,
            }
        ],
        "outputs": [dict(o) for o in outs],
        "outputSchema": [dict(o) for o in outs],
    }
    node["output_schema"] = output_schema
    return node


def _emit_full_dp(step: dict, app_index: dict, taken: set[str]) -> dict:
    ref = _gen_ref("dp", taken)
    node = _node_scaffold(
        DR_NODE_ID, ref, "deep_reasoning", step.get("node_name") or "AI reasoning"
    )
    app_scope = _requested_apps(step, app_index, allow_empty=True)
    outs, output_schema = _dr_outputs(
        step.get("outputs"),
        require_descriptions=step.get("instruction_contract") is not None,
    )
    task_prompt = _render_task_prompt(
        step,
        outs,
        provider_safeguards=_render_full_dp_provider_safeguards(app_scope),
    )
    if _has_contradictory_side_effect_policy(task_prompt):
        raise ValueError("full DP instruction has contradictory success/failure side-effect policy")
    node["config"] = {
        "execution_mode": "workflow",
        "allow_auto_tool_discovery": True,
        "allow_auto_skill_discovery": True,
        "available_tools": [],
        "selected_apps": list(app_scope),
        "only_use_selected_apps": True,
    }
    node["input_map"] = {
        "task_prompt": task_prompt,
        "system_prompt": "",
        "max_steps": 20,
        "knowledge": {"web_urls": ""},
        "tools": _agent_tools(app_scope, app_index),
        "outputs": [dict(o) for o in outs],
        "outputSchema": [dict(o) for o in outs],
    }
    node["output_schema"] = output_schema
    return node


def _emit_condition(cond: dict, taken: set[str]) -> dict:
    ref = _gen_ref("cond", taken)
    node = _node_scaffold(CONDITION_NODE_ID, ref, "condition", cond.get("node_name") or "Condition")
    routes = cond.get("routes")
    if not isinstance(routes, list) or not 1 <= len(routes) <= 6:
        raise ValueError("condition requires 1 to 6 routes")
    switch_map: dict[str, list[dict]] = {}
    determined_by_ai = cond.get("determined_by_ai", False)
    if not isinstance(determined_by_ai, bool):
        raise ValueError("condition determined_by_ai must be boolean")
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError("condition route must be an object")
        route_name = route.get("name")
        if not isinstance(route_name, str):
            raise ValueError("condition route names must be unique, non-empty, and not Default")
        route_name = route_name.strip()
        if not route_name or route_name == "Default" or route_name in switch_map:
            raise ValueError("condition route names must be unique, non-empty, and not Default")
        conditions = route.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise ValueError("condition route requires at least one condition")
        normalized: list[dict] = []
        for item in conditions:
            if not isinstance(item, dict):
                raise ValueError("condition entry must be an object")
            key = item.get("key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError("condition entry key must be a non-empty string")
            if determined_by_ai:
                normalized.append({"key": key})
                continue
            operator = item.get("condition")
            value = item.get("value", "")
            if not isinstance(operator, str) or not operator.strip():
                raise ValueError("condition entry requires string condition and value fields")
            operator = _normalize_condition_operator(operator)
            if operator in _UNARY_CONDITION_OPERATORS and not isinstance(value, str):
                value = ""
            if not isinstance(value, str):
                raise ValueError("condition entry requires string condition and value fields")
            normalized_item = {
                "key": key,
                "condition": operator,
                "value": value,
            }
            join = item.get("join")
            if join is not None:
                if join not in {"and", "or"}:
                    raise ValueError("condition entry join must be and or or")
                normalized_item["join"] = join
            normalized.append(normalized_item)
        switch_map[route_name] = normalized
    config = cond.get("config") or {}
    if config not in ({}, {"evaluatorType": "javascript"}):
        raise ValueError("condition config is unsupported")
    node["config"] = config
    node["input_map"] = {
        "determined_by_ai": determined_by_ai,
        "expression": {"switchConditionMap": switch_map},
    }
    return node


def _html_mock_value_matches(value: object, slot_type: str) -> bool:
    if slot_type in {"string", "unknown"}:
        return isinstance(value, str) and bool(value.strip())
    if slot_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if slot_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if slot_type == "boolean":
        return isinstance(value, bool)
    if slot_type == "array":
        return isinstance(value, list) and bool(value)
    if slot_type == "object":
        return isinstance(value, dict) and bool(value)
    return value is None


def _normalize_html_contract(step: dict) -> tuple[str, list[dict], dict, dict]:
    template = step.get("template")
    slots = step.get("slots")
    parameter = step.get("parameter")
    mock_data = step.get("mock_data")
    if not isinstance(template, str) or not template.strip():
        raise ValueError("HTML step requires a non-empty template")
    if len(template.encode("utf-8")) > _MAX_HTML_TEMPLATE_BYTES:
        raise ValueError("HTML template exceeds the 200000-byte HTML-node limit")
    lowered = template.lower()
    if not lowered.lstrip().startswith("<!doctype html>"):
        raise ValueError("HTML template must start with a HTML5 doctype")
    if any(tag not in lowered for tag in ("<html", "<head", "<body")):
        raise ValueError("HTML template must contain html, head, and body elements")
    if not re.search(r"<meta\b[^>]*\bname\s*=\s*['\"]viewport['\"]", lowered):
        raise ValueError("HTML template must declare a viewport meta tag")
    if any(re.search(rf"<{tag}(?:\s|>)", lowered) for tag in _HTML_FORBIDDEN_TAGS):
        raise ValueError("HTML template contains a forbidden sandbox element")
    if any(api in lowered for api in _HTML_FORBIDDEN_APIS):
        raise ValueError("HTML template contains a forbidden browser capability")
    if _HTML_UNSUPPORTED_DIRECTIVE_RE.search(template):
        raise ValueError("HTML template contains an unsupported template directive")
    if any(
        _REF_RE.fullmatch(match.group(1).strip()) is None
        for match in _HTML_ANY_BRACED_EXPRESSION_RE.finditer(template)
    ):
        raise ValueError("HTML template slots must use flat ${name} expressions")

    if not isinstance(slots, list):
        raise ValueError("HTML step slots must be an array")
    normalized_slots: list[dict] = []
    slot_names: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"name", "type", "required"}:
            raise ValueError("HTML slot fields must be name, type, and required")
        name, slot_type, required = slot.get("name"), slot.get("type"), slot.get("required")
        if (
            not isinstance(name, str)
            or _REF_RE.fullmatch(name) is None
            or name in slot_names
            or slot_type not in _HTML_ALLOWED_SLOT_TYPES
            or not isinstance(required, bool)
        ):
            raise ValueError("HTML step contains an invalid slot declaration")
        slot_names.add(name)
        normalized_slots.append({"name": name, "type": slot_type, "required": required})

    referenced_slots = set(_HTML_SLOT_REFERENCE_RE.findall(template))
    bare_scan_target = _HTML_SLOT_REFERENCE_RE.sub("", template)
    referenced_slots.update(_HTML_BARE_SLOT_REFERENCE_RE.findall(bare_scan_target))
    if referenced_slots != slot_names:
        raise ValueError("HTML template references and declared slots must match exactly")

    if not isinstance(parameter, dict) or set(parameter) != slot_names:
        raise ValueError("HTML parameter keys must match its declared slots")
    for binding in parameter.values():
        if not isinstance(binding, str):
            raise ValueError("HTML parameters must be upstream workflow bindings")
        match = _TEMPLATE_PAIR_RE.fullmatch(binding.strip())
        reference = match.group(1).strip() if match is not None else ""
        reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
        if reference_match is None or any(char in reference_match.group(2) for char in ".[]"):
            raise ValueError("HTML parameters must bind declared top-level workflow outputs")

    if not isinstance(mock_data, dict) or set(mock_data) != slot_names:
        raise ValueError("HTML mock_data keys must match its declared slots")
    if any(
        not _html_mock_value_matches(mock_data[slot["name"]], slot["type"])
        for slot in normalized_slots
    ):
        raise ValueError("HTML mock_data must contain realistic values matching every slot type")
    return template, normalized_slots, dict(parameter), dict(mock_data)


def _normalize_user_message(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("user_message must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("user_message must be a non-empty string")
    if "\n" in normalized or "\r" in normalized:
        raise ValueError("user_message must be a single line")
    if len(normalized) > 200:
        raise ValueError("user_message must not exceed 200 characters")
    return normalized


def _emit_custom_script(step: dict, taken: set[str]) -> dict:
    ref = _gen_ref("code", taken)
    intent = step.get("intent")
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("custom_script intent must be a non-empty string")
    inputs = _normalize_schema_fields(
        step.get("inputs"), label="custom_script inputs", require_non_empty=False
    )
    outputs = _normalize_schema_fields(
        step.get("outputs"), label="custom_script outputs", require_non_empty=True
    )
    outputs_by_name = {output["name"]: output for output in outputs}
    for name, field_type in _REQUIRED_CODE_RELIABILITY_OUTPUTS.items():
        output = outputs_by_name.get(name)
        if output is None or output["type"] != field_type or output["required"] is not True:
            raise ValueError(f"custom_script must declare required {field_type} output '{name}'")
    raw_inputs = step.get("inputs") or []
    parameter = {
        normalized["name"]: _validate_binding_source(raw.get("source"), label="custom_script")
        for raw, normalized in zip(raw_inputs, inputs, strict=True)
    }
    code = _validate_python_artifact(step.get("code"), set(parameter))
    node = _node_scaffold(
        CODE_NODE_ID,
        ref,
        "logic",
        step.get("node_name") or "Custom script",
    )
    node["prompt"] = intent.strip()
    node["node_desc"] = intent.strip()
    node["input_map"] = {
        "input": dict(parameter),
        "code": code,
        "requestJson": {"input_data": dict(parameter), "context": {}},
        "inputSchema": inputs,
        "parameter": dict(parameter),
        "outputSchema": outputs,
        "userMessage": _normalize_user_message(step.get("user_message")),
    }
    node["output_schema"] = {
        "type": "object",
        "properties": {
            output["name"]: {
                "type": "string" if output["type"] == "unknown" else output["type"],
                "description": output["description"],
            }
            for output in outputs
        },
    }
    required_outputs = [output["name"] for output in outputs if output["required"]]
    if required_outputs:
        node["output_schema"]["required"] = required_outputs
    return node


def _emit_html(step: dict, taken: set[str]) -> dict:
    template, slots, parameter, mock_data = _normalize_html_contract(step)
    ref = _gen_ref("html", taken)
    node = _node_scaffold(
        HTML_NODE_ID,
        ref,
        "logic",
        step.get("node_name") or "HTML page",
    )
    node["input_map"] = {
        "template": template,
        "slots": slots,
        "parameter": parameter,
        "userMessage": _normalize_user_message(step.get("user_message")),
    }
    node["config"] = {"mock_data": mock_data}
    node["output_schema"] = {
        "type": "object",
        "properties": {
            "fileId": {
                "type": "string",
                "description": "Owner-scoped stored HTML artifact identifier",
            },
            "url": {"type": "string", "description": "Shareable rendered HTML URL"},
            "content": {
                "type": "object",
                "description": "Stored HTML artifact content metadata",
            },
        },
    }
    return node


def _emit_mobile_notify(step: dict, kind: str, taken: set[str]) -> dict:
    node_id, node_name = _MOBILE_NOTIFY_CHANNELS[kind]
    template_id = step.get("template_id", _MOBILE_NOTIFY_TEMPLATE_ID)
    if template_id not in _MOBILE_NOTIFY_TEMPLATES:
        raise ValueError(
            "mobile notify template_id must be a registered template id: "
            + ", ".join(f"{tid} ({name})" for tid, (name, _) in _MOBILE_NOTIFY_TEMPLATES.items())
        )
    template_name, variable_keys = _MOBILE_NOTIFY_TEMPLATES[template_id]
    recipient = step.get("recipient")
    if not isinstance(recipient, dict):
        raise ValueError("mobile notify requires a recipient object")
    phone_number = recipient.get("phone_number")
    region_code = recipient.get("region_code")
    if not isinstance(phone_number, str) or not _MOBILE_NOTIFY_PHONE_RE.fullmatch(phone_number):
        raise ValueError(
            "mobile notify recipient.phone_number must be digits with an optional leading +"
        )
    if (
        not isinstance(region_code, str)
        or not region_code.startswith("+")
        or not region_code[1:].isdigit()
    ):
        raise ValueError("mobile notify recipient.region_code must carry the + sign (e.g. +1)")
    variables = step.get("variables")
    if not isinstance(variables, dict) or set(variables) != set(variable_keys):
        raise ValueError(
            f"mobile notify variables for {template_name} must declare exactly "
            + ", ".join(variable_keys)
        )
    if any(not isinstance(variables[key], str) for key in variable_keys):
        raise ValueError("mobile notify variable values must be strings")
    ref = _gen_ref("notify", taken)
    node = _node_scaffold(node_id, ref, "notify", step.get("node_name") or node_name)
    node["input_map"] = {
        "templateId": template_id,
        "recipient": {"phoneNumber": phone_number, "regionCode": region_code},
        "variables": {key: variables[key] for key in variable_keys},
    }
    return node


def _rewrite_bindings(nodes: list[dict], id_by_step: dict[str, str]) -> None:
    pairs = sorted(id_by_step.items(), key=lambda kv: len(kv[0]), reverse=True)

    def rw(s: str) -> str:
        for logical, ref in pairs:
            s = s.replace("{{" + logical + ".", "{{" + ref + ".")
            s = s.replace("{{ " + logical + ".", "{{" + ref + ".")
        return s

    def walk(v):
        if isinstance(v, str):
            return rw(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v

    for n in nodes:
        n["input_map"] = walk(n.get("input_map") or {})


def _apply_html_delivery_url_contract(nodes: list[dict], edges: list[dict]) -> None:
    nodes_by_ref = {node.get("reference_id"): node for node in nodes}
    for edge in edges:
        source = nodes_by_ref.get(edge.get("source_node"))
        target = nodes_by_ref.get(edge.get("target_node"))
        if not (
            isinstance(source, dict)
            and source.get("node_id") == HTML_NODE_ID
            and isinstance(target, dict)
            and target.get("node_id") == DR_NODE_ID
        ):
            continue
        input_map = target.get("input_map")
        if not isinstance(input_map, dict):
            continue
        task_prompt = input_map.get("task_prompt")
        if not isinstance(task_prompt, str):
            continue
        if _HTML_DELIVERY_URL_PROMPT_GUARD not in task_prompt:
            input_map["task_prompt"] = (
                f"{task_prompt.rstrip()}\n\n{_HTML_DELIVERY_URL_PROMPT_GUARD}"
            )


def _parse_edge(raw: object) -> tuple[str, str, str | None]:
    if isinstance(raw, list) and len(raw) in {2, 3}:
        source, target = raw[0], raw[1]
        branch = raw[2] if len(raw) == 3 else None
    elif isinstance(raw, dict):
        source = raw.get("source", raw.get("from"))
        target = raw.get("target", raw.get("to"))
        branch = raw.get("branch")
    else:
        raise ValueError("edge must be a two- or three-item array or an object")
    if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
        raise ValueError("edge endpoints must be non-empty logical ids")
    if branch is not None and (not isinstance(branch, str) or not branch.strip()):
        raise ValueError("edge branch must be a non-empty string")
    return source, target, branch


def _polling_fallback_findings(plan: dict, capsules: dict[str, dict]) -> list[str]:
    """Validate the explicit one-hour event-to-polling substitution contract.

    A normal schedule is unaffected. A capsule marked with ``polling_contract`` is different: it
    stands in for an unavailable event trigger, so it must be the first step after an hourly Custom
    schedule and must expose only the source app. Keeping this rule compiler-enforced prevents an
    authored fallback from silently widening its time window or performing a write before matching.

    A request that watches several sources polls each one: ``polling_fallback`` is then a list with
    one entry per poll, in step order. The polls run one after another -- the first straight after
    the schedule, each next one after the previous and nothing else in between -- and the last
    feeds one condition whose success route tests every poll's ``matched`` with ``isTrue``, joined
    by ``or``, so the dependent work runs when any source found something and never otherwise.
    """
    findings: list[str] = []
    steps = plan.get("steps")
    if not isinstance(steps, list):
        steps = []
    polling_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and isinstance(capsules.get(step.get("capsule_id") or ""), dict)
        and capsules[step.get("capsule_id") or ""].get("polling_contract")
    ]
    fallback = plan.get("polling_fallback")

    if not polling_steps:
        if fallback is not None:
            findings.append("polling_fallback requires exactly one bundled polling capsule")
        return findings
    if len(polling_steps) != 1 and not isinstance(fallback, list):
        findings.append("workflow must contain exactly one polling-fallback step")
        return findings
    if not isinstance(fallback, (dict, list)) or fallback == []:
        findings.append("a bundled polling capsule requires polling_fallback metadata")
        return findings
    entries = fallback if isinstance(fallback, list) else [fallback]
    if len(entries) != len(polling_steps):
        findings.append("polling_fallback must list each polling step once, in step order")
        return findings
    if any(
        not isinstance(entry, dict)
        or set(entry) != {"poll_step_id", "source_app", "window_minutes"}
        for entry in entries
    ):
        findings.append("polling_fallback metadata fields are invalid")
        return findings

    poll_ids: list[str] = []
    for index, (entry, poll_step) in enumerate(zip(entries, polling_steps, strict=True)):
        poll_step_id = entry.get("poll_step_id")
        source_app = entry.get("source_app")
        window_minutes = entry.get("window_minutes")
        capsule = capsules[poll_step.get("capsule_id") or ""]
        polling_contract = capsule.get("polling_contract")
        if (
            not isinstance(poll_step_id, str)
            or not poll_step_id
            or not isinstance(source_app, str)
            or not source_app
            or not isinstance(window_minutes, int)
            or isinstance(window_minutes, bool)
        ):
            findings.append("polling_fallback metadata values are invalid")
            return findings
        if (
            not isinstance(polling_contract, dict)
            or polling_contract.get("source_app") != source_app
            or polling_contract.get("window_minutes") != window_minutes
            or window_minutes != 60
        ):
            findings.append("polling_fallback does not match the bundled one-hour polling capsule")
        if (
            poll_step.get("id") != poll_step_id
            or index >= len(steps)
            or steps[index] is not poll_step
        ):
            findings.append(
                "the polling-fallback step must be first after the trigger"
                if index == 0
                else "each further polling step must directly follow the previous one"
            )
        if poll_step.get("kind") != "guided_dp" or poll_step.get("requested_apps") != [source_app]:
            findings.append("the polling-fallback step must be a source-only guided DP")
        instruction_contract = poll_step.get("instruction_contract")
        if not isinstance(instruction_contract, dict) or instruction_contract.get("inputs") != []:
            findings.append("the polling-fallback step must read its source without trigger inputs")
        poll_ids.append(poll_step_id)
    if len({entry.get("source_app") for entry in entries}) != len(entries):
        findings.append("each polling step must watch a different source app")

    trigger = plan.get("trigger")
    input_map = trigger.get("input_map") if isinstance(trigger, dict) else None
    expected_schedule = {
        "frequency": 5,
        "repeatLevel": "hour",
        "repeatEvery": 1,
        "repeatOn": [],
        "monthlyOn": 0,
        "endType": -1,
        "endDate": "",
        "executedTimes": 0,
    }
    if (
        not isinstance(trigger, dict)
        or trigger.get("node_id") != SCHEDULER_TRIGGER_NODE_ID
        or not isinstance(input_map, dict)
        or any(
            input_map.get(key) != value
            or (isinstance(value, int) and isinstance(input_map.get(key), bool))
            for key, value in expected_schedule.items()
        )
    ):
        findings.append("polling_fallback requires an unbounded Custom schedule every one hour")

    raw_edges = plan.get("edges")
    if isinstance(raw_edges, list) and raw_edges:
        parsed_edges: list[tuple[str, str, str | None]] = []
        for raw_edge in raw_edges:
            try:
                parsed_edges.append(_parse_edge(raw_edge))
            except ValueError:
                continue
        first_poll = poll_ids[0]
        trigger_edges = [edge for edge in parsed_edges if edge[0] == "trigger"]
        poll_incoming = [edge for edge in parsed_edges if edge[1] == first_poll]
        if trigger_edges != [("trigger", first_poll, None)] or poll_incoming != [
            ("trigger", first_poll, None)
        ]:
            findings.append("the Custom schedule must connect directly and only to the poll step")
        for previous, current in pairwise(poll_ids):
            link = [(previous, current, None)]
            if [edge for edge in parsed_edges if edge[0] == previous] != link or [
                edge for edge in parsed_edges if edge[1] == current
            ] != link:
                findings.append("each polling step must lead only to the next polling step")
        if len(poll_ids) > 1:
            steps_by_id = {
                step.get("id"): step
                for step in steps
                if isinstance(step, dict) and isinstance(step.get("id"), str)
            }
            leaving = [edge for edge in parsed_edges if edge[0] == poll_ids[-1]]
            gate = (
                steps_by_id.get(leaving[0][1])
                if len(leaving) == 1 and leaving[0][2] is None
                else None
            )
            if not _is_combined_poll_gate(gate, poll_ids):
                findings.append(
                    "the last polling step must lead only to one condition whose success route "
                    "tests every poll's matched output with isTrue, joined by or"
                )
    return list(dict.fromkeys(findings))


def _is_combined_poll_gate(step: object, poll_ids: list[str]) -> bool:
    """Whether a PlanIR condition runs its success route when any of several polls matched.

    Exactly one test per poll, each ``{{<poll>.matched}}`` with ``isTrue``, and ``or`` between them:
    the runtime joins an item to the next with that item's own ``join``, and an absent join is ``and``,
    which would wait for every source to have something at once. A route that also tests every
    poll's ``read_succeeded`` with ``isFalse`` is the same gate in its compiled form (a carried
    workflow), which ``_apply_poll_chain_contract`` produces from the plain one.
    """
    if not isinstance(step, dict) or step.get("kind") != "condition":
        return False
    if step.get("determined_by_ai", False) is not False:
        return False
    matched = {"{{" + poll_id + ".matched}}": "isTrue" for poll_id in poll_ids}
    read = {
        "{{" + poll_id + "." + _POLL_READ_STATUS_OUTPUT + "}}": "isFalse" for poll_id in poll_ids
    }
    for route in step.get("routes") or []:
        conditions = route.get("conditions") if isinstance(route, dict) else None
        if not isinstance(conditions, list) or len(conditions) not in {
            len(poll_ids),
            2 * len(poll_ids),
        }:
            continue
        wanted = matched if len(conditions) == len(poll_ids) else {**matched, **read}
        items = [item for item in conditions if isinstance(item, dict)]
        if len(items) != len(conditions):
            continue
        try:
            tests = {
                str(item.get("key") or "").replace(" ", ""): _normalize_condition_operator(
                    item.get("condition") or ""
                )
                for item in items
            }
        except ValueError:
            continue
        if tests == wanted and all(item.get("join") == "or" for item in items[:-1]):
            return True
    return False


# A chain of polls reports every source it watches. Each poll also says whether its read completed,
# the condition after the chain opens when any read did not, and the step after that condition names
# each source it could not read -- so one unreadable source never costs the others their new items.
# Only a chain changes: a lone poll keeps its exact compiled bytes.
_POLL_READ_STATUS_OUTPUT = "read_succeeded"
_POLL_READ_STATUS_DECLARATION = {
    "name": _POLL_READ_STATUS_OUTPUT,
    "type": "boolean",
    "description": (
        "The read of this source completed for the polling window, whether or not anything matched"
    ),
}
_CHAIN_POLL_PROMPT_HEADING = "## Read status in a multi-source workflow"
_CHAIN_DIGEST_PROMPT_HEADING = "## Watched sources and their read status"


def _chain_poll_step_ids(plan: dict) -> list[str]:
    """Logical ids of a multi-source poll chain in step order; empty for zero or one poll."""
    fallback = plan.get("polling_fallback")
    if not isinstance(fallback, list) or len(fallback) < 2:
        return []
    poll_ids = [entry.get("poll_step_id") for entry in fallback if isinstance(entry, dict)]
    if len(poll_ids) != len(fallback) or not all(
        isinstance(poll_id, str) and poll_id for poll_id in poll_ids
    ):
        return []
    return poll_ids


def _with_read_status_output(step: dict) -> dict:
    """A chained poll step that declares ``read_succeeded``, added when the plan left it out."""
    outputs = step.get("outputs")
    if outputs is not None and not isinstance(outputs, list):
        return step
    if any(
        isinstance(output, dict) and output.get("name") == _POLL_READ_STATUS_OUTPUT
        for output in outputs or []
    ):
        return step
    return {**step, "outputs": [*(outputs or []), dict(_POLL_READ_STATUS_DECLARATION)]}


def _append_prompt_section(node: dict, heading: str, lines: list[str]) -> None:
    input_map = node.get("input_map")
    task_prompt = input_map.get("task_prompt") if isinstance(input_map, dict) else None
    if not isinstance(task_prompt, str) or heading in task_prompt:
        return
    input_map["task_prompt"] = "\n".join([task_prompt, "", heading, *lines])


def _extend_combined_poll_route(switch_map: dict, chain_refs: list[str]) -> str | None:
    """Make the chain's success route also open when a read did not complete.

    Returns the route name, or None when no route is the combined gate. A route that already tests
    every ``read_succeeded`` is left as it is.
    """
    matched = {"{{" + ref + ".matched}}" for ref in chain_refs}
    read = {"{{" + ref + "." + _POLL_READ_STATUS_OUTPUT + "}}" for ref in chain_refs}
    for route_name, items in switch_map.items():
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            continue
        keys = {str(item.get("key") or "").replace(" ", "") for item in items}
        if len(items) == 2 * len(chain_refs) and keys == matched | read:
            return route_name
        if len(items) != len(chain_refs) or keys != matched:
            continue
        items[-1]["join"] = "or"
        for index, ref in enumerate(chain_refs):
            item = {
                "key": "{{" + ref + "." + _POLL_READ_STATUS_OUTPUT + "}}",
                "condition": "isFalse",
                "value": "",
            }
            if index < len(chain_refs) - 1:
                item["join"] = "or"
            items.append(item)
        return route_name
    return None


def _poll_source_name(poll: dict, capsules: dict[str, dict], app_index: dict) -> str:
    """The display name of the app a compiled poll reads."""
    skills = (poll.get("input_map") or {}).get("skills")
    capsule = capsules.get(skills[0].get("name") or "") if isinstance(skills, list) else None
    contract = capsule.get("polling_contract") if isinstance(capsule, dict) else None
    source_app = contract.get("source_app") if isinstance(contract, dict) else None
    meta = app_index.get("apps", {}).get(source_app) if isinstance(source_app, str) else None
    if isinstance(meta, dict) and isinstance(meta.get("app_name"), str):
        return meta["app_name"]
    return source_app if isinstance(source_app, str) else "A watched source"


def _apply_poll_chain_contract(
    nodes: list[dict],
    edges: list[dict],
    chain_refs: list[str],
    capsules: dict[str, dict],
    app_index: dict,
) -> list[str]:
    """Report a source that could not be read instead of failing the whole run.

    Every chained poll gets the read-status section (the DP runtime otherwise treats a failed read as
    a failed step, which ends the run for every source). The combined condition also opens on a read
    that did not complete, and every step on its success route -- an AI step, the one place that sees
    every source -- names each source it could not read and sends nothing when no source found
    anything, so that hour still ends as a failed run with the reason. Topology problems are already
    reported by ``_polling_fallback_findings``; this only applies the contract to a well-formed chain.

    Returns:
        Findings for a success-route step that is not an AI step; empty otherwise.
    """
    if len(chain_refs) < 2:
        return []
    by_ref = {node["reference_id"]: node for node in nodes}
    polls = [by_ref.get(ref) for ref in chain_refs]
    if any(poll is None or poll.get("node_id") != DR_NODE_ID for poll in polls):
        return []
    for poll in polls:
        _append_prompt_section(
            poll,
            _CHAIN_POLL_PROMPT_HEADING,
            [
                "This workflow watches several sources and reports any source it could not read, "
                "so a failed read is a result of this step, not a failure of it.",
                "- Set `read_succeeded=true` when the read of this source completed, whether or not "
                "anything matched.",
                "- When the read fails for any reason, including a service error, a timeout, or a "
                "permission error, set `read_succeeded=false`, `matched=false`, and an empty "
                "`matched_items`, name the source that could not be read in `response`, and finish "
                "with <task_status>fully_completed</task_status>.",
            ],
        )
    leaving = [edge for edge in edges if edge.get("source_node") == chain_refs[-1]]
    gate = (
        by_ref.get(leaving[0].get("target_node"))
        if len(leaving) == 1 and not leaving[0].get("condition")
        else None
    )
    if gate is None or gate.get("node_id") != CONDITION_NODE_ID:
        return []
    route = _extend_combined_poll_route(
        gate["input_map"]["expression"]["switchConditionMap"], chain_refs
    )
    if route is None:
        return []
    sources = [
        (_poll_source_name(poll, capsules, app_index), poll["reference_id"]) for poll in polls
    ]
    status_lines = [
        f"- {name} — new items found = {{{{{ref}.matched}}}}, read completed = "
        f"{{{{{ref}.{_POLL_READ_STATUS_OUTPUT}}}}}"
        for name, ref in sources
    ]
    findings: list[str] = []
    for edge in edges:
        if edge.get("source_node") != gate["reference_id"]:
            continue
        if next(iter((edge.get("condition") or {}).values()), None) != route:
            continue
        consumer = by_ref.get(edge.get("target_node"))
        if consumer is None:
            continue
        if consumer.get("node_id") != DR_NODE_ID:
            findings.append(
                "in a workflow that watches several sources, the step after the combined "
                "condition must be a guided_dp or full_dp that merges the sources and reports "
                "any source it could not read"
            )
            continue
        _append_prompt_section(
            consumer,
            _CHAIN_DIGEST_PROMPT_HEADING,
            [
                "This step covers several watched sources. What each source returned in this run:",
                *status_lines,
                "- For every source whose read did not complete, add one line to the result saying "
                "that this source could not be read this time, so it is not included.",
                "- When no source found new items, do not send, post, or write anything, and finish "
                "with <task_status>incomplete</task_status> and a task_failure_reason naming each "
                "source that could not be read.",
            ],
        )
    return findings


def _polling_refs(nodes: list[dict], capsules: dict[str, dict]) -> set[str]:
    """Reference ids of the compiled DPs whose capsule is a polling fallback."""
    refs: set[str] = set()
    for node in nodes:
        skills = (node.get("input_map") or {}).get("skills")
        if not isinstance(skills, list) or len(skills) != 1 or not isinstance(skills[0], dict):
            continue
        capsule = capsules.get(skills[0].get("name") or "")
        if isinstance(capsule, dict) and capsule.get("polling_contract"):
            refs.add(node["reference_id"])
    return refs


def _chain_outgoing(producer_ref: str, edges: list[dict], poll_refs: set[str]) -> list[dict]:
    """The edges that carry a producer's result onward, following a chain of polls.

    One poll's plain link to the next is sequencing, not a dependent. The edges that leave the
    chain's last poll are every poll's dependents, so each poll meets the same success gate and
    payload rule as a lone one. Any other producer keeps exactly its own edges.
    """
    if producer_ref not in poll_refs:
        return [edge for edge in edges if edge.get("source_node") == producer_ref]
    leaving: list[dict] = []
    seen = {producer_ref}
    frontier = [producer_ref]
    while frontier:
        ref = frontier.pop()
        for edge in edges:
            if edge.get("source_node") != ref:
                continue
            target = edge.get("target_node")
            if target in poll_refs and not edge.get("condition"):
                if target not in seen:
                    seen.add(target)
                    frontier.append(target)
                continue
            leaving.append(edge)
    return leaving


def compile_plan(plan: dict, *, allow_html_node: bool = False) -> dict:
    if not isinstance(plan, dict):
        return {"status": "rejected", "findings": ["PlanIR must be an object"]}
    by_id = {(n.get("action_id") or n.get("node_id")): n for n in _load(CATALOG)["items"]}
    capsules = {c["capsule_id"]: c for c in _load(CAPSULE_CATALOG)["capsules"]}
    app_index = _load(APP_INDEX)

    findings: list[str] = _polling_fallback_findings(plan, capsules)
    chain_poll_ids = _chain_poll_step_ids(plan)
    taken: set[str] = set()
    trigger = plan.get("trigger") or {}
    if not isinstance(trigger, dict) or not trigger.get("node_id"):
        return {"status": "rejected", "findings": ["missing trigger.node_id"]}

    id_by_step: dict[str, str] = {}
    nodes: list[dict] = []
    try:
        trg = _emit_trigger(trigger, by_id, taken)
    except ValueError as exc:
        return {"status": "rejected", "findings": [str(exc)]}
    except (KeyError, TypeError):
        return {"status": "rejected", "findings": ["trigger contract is invalid"]}
    nodes.append(trg)
    id_by_step["trigger"] = trg["reference_id"]

    raw_steps = plan.get("steps") or []
    if not isinstance(raw_steps, list) or not raw_steps:
        return {"status": "rejected", "findings": ["PlanIR requires at least one workflow step"]}
    html_steps = [
        step for step in raw_steps if isinstance(step, dict) and step.get("kind") == "html"
    ]
    html_requested = plan.get("html_node_requested") is True
    if html_steps and not allow_html_node:
        findings.append("HTML-node creation is not permitted for this build")
    if html_steps and not html_requested:
        findings.append("HTML PlanIR requires html_node_requested=true")
    if html_requested and not html_steps:
        findings.append("html_node_requested=true requires at least one HTML step")
    if html_steps and not any(
        isinstance(step, dict) and step.get("kind") in {"guided_dp", "full_dp", "custom_script"}
        for step in raw_steps
    ):
        findings.append("an HTML workflow requires an upstream DP step")
    emitted_ids: list[str] = []
    seen_step_ids = {"trigger"}
    for step in raw_steps:
        if not isinstance(step, dict):
            findings.append("step must be an object")
            continue
        step_id = step.get("id")
        if (
            not isinstance(step_id, str)
            or not _REF_RE.fullmatch(step_id)
            or step_id in seen_step_ids
        ):
            findings.append("step id must be unique and identifier-safe")
            continue
        seen_step_ids.add(step_id)
        kind = step.get("kind")
        if kind in {"guided_dp", "full_dp"} and not (
            isinstance(step.get("intent"), str) and step["intent"].strip()
        ):
            findings.append("DP step intent must be a non-empty string")
            continue
        try:
            if kind == "guided_dp":
                cap = capsules.get(step.get("capsule_id") or "")
                if not cap:
                    findings.append("guided DP capsule_id is unknown")
                    continue
                extra_apps = [
                    key
                    for key in (step.get("requested_apps") or [])
                    if key not in (cap.get("app_scope") or [])
                ]
                if extra_apps:
                    findings.append(
                        "guided DP cannot add apps beyond its capsule scope; "
                        "use full_dp or a capsule that covers them"
                    )
                    continue
                emit_step = _with_read_status_output(step) if step_id in chain_poll_ids else step
                node = _emit_guided_dp(emit_step, cap, app_index, taken)
            elif kind == "full_dp":
                node = _emit_full_dp(step, app_index, taken)
            elif kind == "condition":
                node = _emit_condition(step, taken)
            elif kind == "custom_script":
                node = _emit_custom_script(step, taken)
            elif kind == "html":
                if not allow_html_node:
                    continue
                node = _emit_html(step, taken)
            elif kind in _MOBILE_NOTIFY_CHANNELS:
                node = _emit_mobile_notify(step, kind, taken)
            else:
                findings.append("unsupported Phase-1 step kind")
                continue
        except ValueError as exc:
            findings.append(str(exc))
            continue
        except (KeyError, OSError, TypeError):
            findings.append("step contract is invalid")
            continue
        nodes.append(node)
        id_by_step[step_id] = node["reference_id"]
        emitted_ids.append(step_id)

    _rewrite_bindings(nodes, id_by_step)

    raw_edges = plan.get("edges") or []
    has_condition = any(node["node_id"] == CONDITION_NODE_ID for node in nodes)
    if not raw_edges and len(nodes) > 1:
        if has_condition:
            findings.append("condition graphs require explicit branch edges")
        else:
            logical_chain = ["trigger", *emitted_ids]
            raw_edges = [list(pair) for pair in pairwise(logical_chain)]
    if not isinstance(raw_edges, list):
        findings.append("edges must be an array")
        raw_edges = []

    nodes_by_ref = {node["reference_id"]: node for node in nodes}
    edges: list[dict] = []
    for raw_edge in raw_edges:
        try:
            source_id, target_id, branch = _parse_edge(raw_edge)
        except ValueError:
            findings.append("edge contract is invalid")
            continue
        source_ref, target_ref = id_by_step.get(source_id), id_by_step.get(target_id)
        if not source_ref or not target_ref:
            findings.append("edge references an unknown logical step")
            continue
        source_node = nodes_by_ref[source_ref]
        edge = {"source_node": source_ref, "target_node": target_ref}
        if source_node["node_id"] == CONDITION_NODE_ID:
            switch_map = source_node["input_map"]["expression"]["switchConditionMap"]
            if branch not in {*switch_map, "Default"}:
                findings.append("condition edge branch is missing or unknown")
                continue
            edge["condition"] = {f"{source_ref}.branch": branch}
        elif branch is not None:
            findings.append("only condition edges may declare a branch")
            continue
        edges.append(edge)

    _apply_html_delivery_url_contract(nodes, edges)
    findings += _apply_poll_chain_contract(
        nodes,
        edges,
        [id_by_step[step_id] for step_id in chain_poll_ids if step_id in id_by_step],
        capsules,
        app_index,
    )

    name = plan.get("name") or "Zoom Workflow"
    description = plan.get("description")
    if not isinstance(name, str) or (description is not None and not isinstance(description, str)):
        findings.append("workflow name and description must be strings")
        name, description = "Zoom Workflow", "Zoom Workflow automation"
    else:
        name = name.strip() or "Zoom Workflow"
        description = description.strip() if isinstance(description, str) else ""
        if not description:
            description = f"{name} automation"
    workflow = _assemble(nodes, edges, name, description)
    findings += _structural_validate(nodes, edges, capsules)
    capsule_body_sizes: list[int] = []
    for node in nodes:
        skills = node.get("input_map", {}).get("skills")
        if not isinstance(skills, list):
            continue
        for skill in skills:
            if isinstance(skill, dict) and isinstance(skill.get("md_content"), str):
                capsule_body_sizes.append(len(skill["md_content"].encode("utf-8")))
    if len(capsule_body_sizes) > 1 and sum(capsule_body_sizes) > _MAX_MULTI_CAPSULE_BODY_BYTES:
        findings.append(
            "multiple guided DP capsules exceed the 65000-byte combined-body budget; keep only "
            "the highest-value guided DP and fold the remaining work into one terminal full DP"
        )
    compiled_bytes = len(json.dumps(workflow, indent=2).encode("utf-8"))
    if compiled_bytes > _MAX_COMPILED_WORKFLOW_BYTES:
        findings.append(
            f"compiled workflow exceeds the {_MAX_COMPILED_WORKFLOW_BYTES}-byte persistence "
            "budget; keep only the "
            "highest-value guided DP and fold the remaining work into one terminal full DP"
        )
    status = "rejected" if findings else "compiled"
    return {"status": status, "workflow": workflow, "findings": findings}


def _assemble(nodes: list[dict], edges: list[dict], name: str, description: str) -> dict:
    fb = uuid.uuid4().hex[:24]
    return {
        "version": 1,
        "exportedAt": "1970-01-01T00:00:00.000Z",
        "data": {
            "metadata": {
                "flowBookId": fb,
                "name": name,
                "description": description,
                "source": "",
                "sessionId": str(uuid.uuid4()),
            },
            "flows": [
                {
                    "workflow_metadata": {
                        "flow_id": f"{fb}_1",
                        "name": name,
                        "description": description,
                    },
                    "nodes": nodes,
                    "edges": edges,
                }
            ],
        },
    }


def _structural_validate(
    nodes: list[dict], edges: list[dict], capsules: dict[str, dict]
) -> list[str]:
    findings: list[str] = []
    triggers = [node for node in nodes if node["node_type"] == "trigger"]
    if len(triggers) != 1:
        findings.append("workflow must contain exactly one trigger")
    refs = {node["reference_id"] for node in nodes}
    nodes_by_ref = {node["reference_id"]: node for node in nodes}
    adjacency: dict[str, set[str]] = {reference_id: set() for reference_id in refs}
    incoming: dict[str, set[str]] = {reference_id: set() for reference_id in refs}
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in edges:
        source, target = edge.get("source_node"), edge.get("target_node")
        if source not in refs or target not in refs or source == target:
            findings.append("edge has an invalid endpoint")
            continue
        condition_key = json.dumps(edge.get("condition"), sort_keys=True)
        identity = (source, target, condition_key)
        if identity in seen_edges:
            findings.append("workflow contains a duplicate edge")
            continue
        seen_edges.add(identity)
        adjacency[source].add(target)
        incoming[target].add(source)

    def reachable(start: str) -> set[str]:
        visited: set[str] = set()
        stack = list(adjacency[start])
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(adjacency[current])
        return visited

    def resolve_binding_schema(source: object, consumer_ref: str, label: str) -> dict | None:
        if not isinstance(source, str):
            findings.append(f"{label} must be a workflow binding string")
            return None
        match = _TEMPLATE_PAIR_RE.fullmatch(source.strip())
        reference = match.group(1).strip().partition("|")[0].strip() if match else ""
        reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
        if reference_match is None:
            findings.append(f"{label} must bind one declared node output field")
            return None
        producer, raw_path = reference_match.groups()
        if "." in raw_path or "[" in raw_path or "]" in raw_path:
            findings.append(f"{label} must bind a top-level output field")
            return None
        producer_node = nodes_by_ref.get(producer)
        if producer_node is None:
            findings.append(f"{label} references an unknown node")
            return None
        if producer == consumer_ref or consumer_ref not in reachable(producer):
            findings.append(f"{label} must reference an upstream node")
            return None
        producer_outputs = producer_node.get("output_schema", {}).get("properties", {})
        output_schema = (
            producer_outputs.get(raw_path) if isinstance(producer_outputs, dict) else None
        )
        if not isinstance(output_schema, dict):
            findings.append(f"{label} references an undeclared output field")
            return None
        return output_schema

    def validate_custom_script(node: dict) -> None:
        reference_id = node["reference_id"]
        prompt = node.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            findings.append("custom_script must persist a non-empty prompt")
        input_map = node.get("input_map")
        if not isinstance(input_map, dict) or set(input_map) != {
            "input",
            "code",
            "requestJson",
            "inputSchema",
            "parameter",
            "outputSchema",
            "userMessage",
        }:
            findings.append("custom_script input_map contract is invalid")
            return
        parameter = input_map.get("parameter")
        input_value = input_map.get("input")
        request_json = input_map.get("requestJson")
        input_schema = input_map.get("inputSchema")
        output_schema = input_map.get("outputSchema")
        if (
            not isinstance(parameter, dict)
            or input_value != parameter
            or request_json != {"input_data": parameter, "context": {}}
            or not isinstance(input_schema, list)
            or not isinstance(output_schema, list)
        ):
            findings.append("custom_script runtime input contract is inconsistent")
            return
        input_fields = {
            item.get("name"): item
            for item in input_schema
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        if set(input_fields) != set(parameter) or len(input_fields) != len(input_schema):
            findings.append("custom_script inputSchema does not match its parameter bindings")
        for name, source in parameter.items():
            producer_schema = resolve_binding_schema(
                source, reference_id, "custom_script parameter binding"
            )
            declared = input_fields.get(name)
            if producer_schema is None or not isinstance(declared, dict):
                continue
            producer_type = producer_schema.get("type")
            declared_type = declared.get("type")
            compatible = producer_type == declared_type or (
                declared_type == "number" and producer_type == "integer"
            )
            if declared_type != "unknown" and not compatible:
                findings.append("custom_script input type does not match its producer output")
        emitted_outputs = node.get("output_schema", {}).get("properties", {})
        output_fields = {
            item.get("name"): item
            for item in output_schema
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        if (
            not output_fields
            or len(output_fields) != len(output_schema)
            or not isinstance(emitted_outputs, dict)
            or set(output_fields) != set(emitted_outputs)
        ):
            findings.append("custom_script output declarations are inconsistent")
        try:
            _validate_python_artifact(input_map.get("code"), set(parameter))
        except ValueError as exc:
            findings.append(str(exc))

    poll_refs = _polling_refs(nodes, capsules)
    for producer_node in nodes:
        producer_ref = producer_node["reference_id"]
        skills = producer_node.get("input_map", {}).get("skills")
        if not isinstance(skills, list) or len(skills) != 1 or not isinstance(skills[0], dict):
            continue
        capsule = capsules.get(skills[0].get("name") or "")
        downstream_contract = (
            capsule.get("downstream_contract") if isinstance(capsule, dict) else None
        )
        entry_gate_contract = (
            capsule.get("entry_gate_contract") if isinstance(capsule, dict) else None
        )
        if isinstance(entry_gate_contract, dict) and entry_gate_contract:
            source_node_ids = entry_gate_contract.get("source_node_ids")
            source_output = entry_gate_contract.get("source_output")
            if (
                not isinstance(source_node_ids, list)
                or not source_node_ids
                or not all(isinstance(node_id, str) and node_id for node_id in source_node_ids)
                or not isinstance(source_output, str)
                or not source_output
            ):
                findings.append("guided DP entry-gate contract is invalid")
            elif len(triggers) == 1:
                trigger_node = triggers[0]
                trigger_ref = trigger_node["reference_id"]
                if trigger_node.get("node_id") not in source_node_ids:
                    findings.append("guided DP entry gate is attached to an unsupported trigger")
                if incoming[producer_ref] != {trigger_ref}:
                    findings.append("guided DP entry gate must run directly after the trigger")
                if adjacency[trigger_ref] != {producer_ref}:
                    findings.append("workflow work must not bypass its guided DP entry gate")
                if not adjacency[producer_ref]:
                    findings.append("guided DP entry gate must guard downstream workflow work")
                bindings = {
                    match.group(1).strip().partition("|")[0].strip()
                    for value in _iter_strings(producer_node.get("input_map", {}))
                    for match in _TEMPLATE_PAIR_RE.finditer(value)
                }
                if f"{trigger_ref}.{source_output}" not in bindings:
                    findings.append("guided DP entry gate must bind its declared trigger output")
        if not isinstance(downstream_contract, dict) or not downstream_contract:
            continue
        outgoing_edges = _chain_outgoing(producer_ref, edges, poll_refs)
        if not outgoing_edges:
            continue
        success_output = downstream_contract.get("success_output")
        alternate_success_outputs = downstream_contract.get("alternate_success_outputs") or []
        payload_outputs = downstream_contract.get("payload_outputs")
        if (
            not isinstance(success_output, str)
            or not success_output
            or not isinstance(alternate_success_outputs, list)
            or not all(
                isinstance(output, str) and bool(output) for output in alternate_success_outputs
            )
            or not isinstance(payload_outputs, list)
            or not all(isinstance(output, str) and bool(output) for output in payload_outputs)
        ):
            findings.append("guided DP downstream contract is invalid")
            continue
        success_outputs = {success_output, *alternate_success_outputs}
        producer_outputs = producer_node.get("output_schema", {}).get("properties", {})
        if not isinstance(producer_outputs, dict) or any(
            not isinstance(producer_outputs.get(output), dict)
            or producer_outputs[output].get("type") != "boolean"
            for output in success_outputs
        ):
            findings.append("guided DP downstream success outputs must be declared booleans")
            continue
        if any(output not in producer_outputs for output in payload_outputs):
            findings.append("guided DP downstream payload outputs must be declared")
            continue
        for outgoing_edge in outgoing_edges:
            condition_node = nodes_by_ref.get(outgoing_edge.get("target_node"))
            if not condition_node or condition_node.get("node_id") != CONDITION_NODE_ID:
                findings.append(
                    "a guided DP with dependent downstream work must first route through its "
                    "typed success condition"
                )
                continue
            if condition_node.get("input_map", {}).get("determined_by_ai") is not False:
                findings.append(
                    "dependent downstream work must use a deterministic typed success condition"
                )
                continue
            switch_map = (
                condition_node.get("input_map", {})
                .get("expression", {})
                .get("switchConditionMap", {})
            )
            expected_keys = {f"{{{{{producer_ref}.{output}}}}}" for output in success_outputs}
            success_routes = {
                route_name
                for route_name, conditions in switch_map.items()
                if any(
                    isinstance(item, dict)
                    and item.get("key") in expected_keys
                    and item.get("condition") == "isTrue"
                    for item in conditions
                )
            }
            if not success_routes:
                findings.append(
                    "dependent downstream work must use the capsule's typed success output "
                    "with isTrue"
                )
                continue
            for condition_edge in edges:
                if condition_edge.get("source_node") != condition_node["reference_id"]:
                    continue
                branch = next(iter(condition_edge.get("condition", {}).values()), None)
                if branch not in success_routes:
                    continue
                consumer = nodes_by_ref.get(condition_edge.get("target_node"))
                if consumer is None:
                    continue
                bindings = {
                    match.group(1).strip().partition("|")[0].strip()
                    for value in _iter_strings(consumer.get("input_map", {}))
                    for match in _TEMPLATE_PAIR_RE.finditer(value)
                }
                missing_payloads = [
                    output
                    for output in payload_outputs
                    if isinstance(output, str) and f"{producer_ref}.{output}" not in bindings
                ]
                if missing_payloads:
                    findings.append(
                        "dependent downstream work must bind the capsule's typed payload output"
                    )

    for node in nodes:
        reference_id = node["reference_id"]
        if not _REF_RE.fullmatch(reference_id):
            findings.append("compiler emitted an invalid reference_id")
        node_id = node["node_id"]
        if node["node_type"] == "trigger":
            continue
        if node_id not in {
            DR_NODE_ID,
            CONDITION_NODE_ID,
            CODE_NODE_ID,
            HTML_NODE_ID,
            VOICE_NODE_ID,
            SMS_NODE_ID,
        }:
            findings.append("workflow contains a node outside the planner_v3 palette")
            continue
        if reference_id not in incoming or not incoming[reference_id]:
            findings.append("workflow contains an unreachable node")

        if node_id == CODE_NODE_ID:
            validate_custom_script(node)
            continue

        if node_id == CONDITION_NODE_ID:
            switch_map = node["input_map"].get("expression", {}).get("switchConditionMap", {})
            outgoing_branches = {
                next(iter(edge.get("condition", {}).values()), None)
                for edge in edges
                if edge.get("source_node") == reference_id
            }
            if not set(switch_map) <= outgoing_branches:
                findings.append("condition route is missing an outgoing branch edge")
            determined_by_ai = node["input_map"].get("determined_by_ai")
            for conditions in switch_map.values():
                for item in conditions:
                    key = item.get("key", "")
                    match = _TEMPLATE_PAIR_RE.fullmatch(key.strip())
                    if match is None:
                        findings.append("condition key must bind to an upstream output field")
                        continue
                    reference = match.group(1).strip().partition("|")[0].strip()
                    reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
                    if reference_match is None:
                        findings.append("condition key must bind to an upstream output field")
                        continue
                    producer, raw_path = reference_match.groups()
                    producer_node = nodes_by_ref.get(producer)
                    if producer_node is None:
                        findings.append("condition key references an unknown node")
                        continue
                    if producer == reference_id or reference_id not in reachable(producer):
                        findings.append("condition key must reference an upstream node")
                        continue
                    if "." in raw_path or "[" in raw_path or "]" in raw_path:
                        findings.append(
                            "condition key must bind a declared top-level output field; "
                            "pass whole objects to a DP and inspect nested fields there"
                        )
                        continue
                    output_field = raw_path
                    producer_outputs = producer_node.get("output_schema", {}).get("properties", {})
                    output_schema = (
                        producer_outputs.get(output_field)
                        if isinstance(producer_outputs, dict)
                        else None
                    )
                    if not isinstance(output_schema, dict):
                        findings.append("condition key references an undeclared output field")
                        continue
                    if determined_by_ai:
                        continue
                    operator = item.get("condition")
                    output_type = output_schema.get("type")
                    if isinstance(output_type, str):
                        output_types = {output_type}
                    elif isinstance(output_type, list):
                        output_types = {value for value in output_type if isinstance(value, str)}
                    else:
                        output_types = set()
                    if operator in _BOOLEAN_CONDITION_OPERATORS and "boolean" not in output_types:
                        findings.append("isTrue/isFalse conditions require a boolean output")
                    if operator in _NUMERIC_CONDITION_OPERATORS and not output_types & {
                        "integer",
                        "number",
                    }:
                        findings.append("numeric conditions require an integer or number output")
                    negative_delivery_test = operator == "isFalse" or (
                        operator == "eq"
                        and str(item.get("value", "")).strip().lower()
                        in {"false", "failed", "failure"}
                    )
                    if (
                        "fallback_required" in producer_outputs
                        and output_field in {"delivery_succeeded", "delivery_status"}
                        and negative_delivery_test
                    ):
                        findings.append(
                            "delivery fallback branches must use fallback_required with isTrue "
                            "so no-data runs do not trigger fallback"
                        )
            continue

        if node_id == HTML_NODE_ID:
            if node.get("node_type") != "logic":
                findings.append("HTML node must use the Workflow logic node type")
            successors = adjacency[reference_id]
            if len(successors) > 1:
                findings.append("HTML node may feed at most one link-delivery DP")
            elif successors:
                successor_ref = next(iter(successors))
                successor = nodes_by_ref[successor_ref]
                if successor.get("node_id") != DR_NODE_ID:
                    findings.append("HTML node may only feed a DP that delivers its URL")
                else:
                    if adjacency[successor_ref]:
                        findings.append("HTML link-delivery DP must be terminal")
                    url_binding = f"{reference_id}.url"
                    successor_bindings = {
                        match.group(1).strip()
                        for value in _iter_strings(successor.get("input_map", {}))
                        for match in _TEMPLATE_PAIR_RE.finditer(value)
                    }
                    if url_binding not in successor_bindings:
                        findings.append(
                            "HTML link-delivery DP must use the exact canvas-safe HTML url binding"
                        )
                    task_prompt = successor.get("input_map", {}).get("task_prompt")
                    if (
                        not isinstance(task_prompt, str)
                        or _HTML_DELIVERY_URL_PROMPT_GUARD not in task_prompt
                    ):
                        findings.append(
                            "HTML link-delivery DP must include the compiler-owned URL "
                            "normalization contract"
                        )
            try:
                _normalize_html_contract(
                    {
                        "template": node.get("input_map", {}).get("template"),
                        "slots": node.get("input_map", {}).get("slots"),
                        "parameter": node.get("input_map", {}).get("parameter"),
                        "mock_data": node.get("config", {}).get("mock_data"),
                    }
                )
            except (AttributeError, TypeError, ValueError) as exc:
                findings.append(str(exc))
                continue
            template = node["input_map"]["template"]
            for slot_name, binding in node["input_map"]["parameter"].items():
                match = _TEMPLATE_PAIR_RE.fullmatch(binding.strip())
                reference = match.group(1).strip() if match is not None else ""
                reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
                if reference_match is None:
                    findings.append("HTML parameter must bind a declared upstream output")
                    continue
                producer, output_field = reference_match.groups()
                producer_node = nodes_by_ref.get(producer)
                producer_outputs = (
                    producer_node.get("output_schema", {}).get("properties")
                    if isinstance(producer_node, dict)
                    else None
                )
                if not isinstance(producer_outputs, dict) or output_field not in producer_outputs:
                    findings.append("HTML parameter references an undeclared output field")
                if (
                    isinstance(producer_node, dict)
                    and producer_node.get("node_id") == DR_NODE_ID
                    and output_field == "response"
                    and _html_slot_is_json_payload(template, slot_name)
                ):
                    findings.append(
                        "HTML JSON-parsed slots must bind a dedicated DP output, not the "
                        "receipt-prefixed response"
                    )
                if (
                    producer_node is None
                    or producer == reference_id
                    or reference_id not in reachable(producer)
                ):
                    findings.append("HTML parameter must reference an upstream node")
            continue

        if node_id in {VOICE_NODE_ID, SMS_NODE_ID}:
            if node["node_type"] != "notify":
                findings.append("mobile notify node must use the notify node type")
            if adjacency[reference_id]:
                findings.append("mobile notify node must be terminal")
            for value in _iter_strings(node.get("input_map", {})):
                if "{{" in _TEMPLATE_PAIR_RE.sub("", value):
                    findings.append("mobile notify contains a malformed workflow binding")
                for match in _TEMPLATE_PAIR_RE.finditer(value):
                    reference = match.group(1).strip().partition("|")[0].strip()
                    if reference in _MOBILE_NOTIFY_CREATOR_BINDINGS:
                        continue
                    reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
                    if reference_match is None:
                        findings.append("mobile notify binding must name a node output field")
                        continue
                    producer, raw_path = reference_match.groups()
                    if producer not in refs:
                        findings.append("mobile notify binding references an unknown node")
                        continue
                    top, _, nested = raw_path.partition(".")
                    if "." in nested or "[" in raw_path or "]" in raw_path:
                        findings.append(
                            "mobile notify binding must bind a declared output field"
                        )
                        continue
                    producer_outputs = (
                        nodes_by_ref[producer].get("output_schema", {}).get("properties")
                    )
                    if not isinstance(producer_outputs, dict) or top not in producer_outputs:
                        findings.append(
                            "mobile notify binding references an undeclared output field"
                        )
                    elif nested and (
                        nodes_by_ref[producer]["node_type"] != "trigger"
                        or nested not in (producer_outputs[top].get("properties") or {})
                    ):
                        findings.append(
                            "mobile notify binding may name a nested field only when the trigger declares it"
                        )
                    if producer == reference_id or reference_id not in reachable(producer):
                        findings.append(
                            "mobile notify binding references a node that is not upstream"
                        )
            continue

        config = node.get("config", {})
        input_map = node.get("input_map", {})
        selected_apps = config.get("selected_apps")
        available_tools = config.get("available_tools")
        grouped_tools = input_map.get("tools")
        if (
            config.get("execution_mode") != "workflow"
            or config.get("allow_auto_tool_discovery") is not True
            or config.get("only_use_selected_apps") is not True
            or not isinstance(config.get("allow_auto_skill_discovery"), bool)
        ):
            findings.append("DP config is missing the explicit workflow discovery contract")
        if (
            not isinstance(selected_apps, list)
            or any(not isinstance(key, str) or not key for key in selected_apps)
            or len(selected_apps) != len(set(selected_apps))
            or not isinstance(available_tools, list)
            or any(not isinstance(tool, str) or not tool for tool in available_tools)
        ):
            findings.append("DP app or tool scope is invalid")
        if (
            not isinstance(grouped_tools, list)
            or any(not isinstance(tool, dict) for tool in grouped_tools)
            or [tool.get("app_key") for tool in grouped_tools] != selected_apps
        ):
            findings.append("DP grouped tools do not match selected_apps")
        elif any(
            not isinstance(tool, dict)
            or not isinstance(tool.get("app_name"), str)
            or tool.get("source") not in {"connector", "workplace"}
            or tool.get("tool_details") != []
            for tool in grouped_tools
        ):
            findings.append("DP grouped tool shape is invalid")
        if (
            not isinstance(input_map.get("task_prompt"), str)
            or not input_map["task_prompt"].strip()
        ):
            findings.append("DP task_prompt must be non-empty")
        if not isinstance(input_map.get("max_steps"), int) or not 1 <= input_map["max_steps"] <= 50:
            findings.append("DP max_steps is outside the supported bound")

        output_names = {
            item.get("name") for item in input_map.get("outputs", []) if isinstance(item, dict)
        }
        schema_names = set(node.get("output_schema", {}).get("properties") or {})
        mirror_names = {
            item.get("name") for item in input_map.get("outputSchema", []) if isinstance(item, dict)
        }
        if (
            not output_names
            or output_names != schema_names
            or output_names != mirror_names
            or "response" not in output_names
        ):
            findings.append("DP output declarations are inconsistent")

        skills = input_map.get("skills")
        if config.get("allow_auto_skill_discovery") is False:
            if not isinstance(skills, list) or len(skills) != 1:
                findings.append("guided DP must carry exactly one dynamic Skill")
            else:
                skill = skills[0]
                if (
                    not isinstance(skill, dict)
                    or skill.get("skill_type") != "dynamic"
                    or not isinstance(skill.get("name"), str)
                    or not skill.get("name")
                    or not isinstance(skill.get("description"), str)
                    or not skill.get("description")
                    or not isinstance(skill.get("md_content"), str)
                    or not skill.get("md_content")
                    or skill.get("required_tools") != available_tools
                ):
                    findings.append("guided DP dynamic Skill contract is invalid")
                if isinstance(skill, dict):
                    capsule = capsules.get(skill.get("name") or "")
                    capsule_output_names = {
                        item.get("name")
                        for item in (capsule or {}).get("typed_outputs", [])
                        if isinstance(item, dict)
                    }
                    if not capsule_output_names <= output_names:
                        findings.append("guided DP is missing bundled capsule outputs")
                    task_prompt_guards = (capsule or {}).get("task_prompt_guards") or []
                    task_prompt = input_map.get("task_prompt")
                    if isinstance(task_prompt_guards, list) and isinstance(task_prompt, str):
                        if any(
                            not isinstance(guard, str)
                            or not guard.strip()
                            or f"- {guard.strip()}" not in task_prompt
                            for guard in task_prompt_guards
                        ):
                            findings.append("guided DP is missing bundled task-prompt guards")
                if available_tools and not selected_apps:
                    findings.append("guided DP tools require a non-empty app scope")
        else:
            if skills not in (None, []):
                findings.append("full DP must not carry an explicit Skill")
            if available_tools != []:
                findings.append("full DP must rely on runtime tool discovery")
            successors = adjacency[reference_id]
            if successors:
                successor_ids = {nodes_by_ref[successor].get("node_id") for successor in successors}
                allowed_successor = (
                    successor_ids == {HTML_NODE_ID}
                    or (
                        len(successors) == 1
                        and successor_ids == {CODE_NODE_ID}
                        and selected_apps == []
                    )
                    or (len(successors) == 1 and successor_ids <= {VOICE_NODE_ID, SMS_NODE_ID})
                )
                if not allowed_successor:
                    findings.append(
                        "full DP must be terminal except for terminal HTML renderers, a "
                        "Custom Script fed by a tool-free full DP, or a mobile-notify node"
                    )

        for value in (*_iter_strings(input_map), *_iter_strings(config)):
            if "{{" in _TEMPLATE_PAIR_RE.sub("", value):
                findings.append("DP contains a malformed workflow binding")
            for match in _TEMPLATE_PAIR_RE.finditer(value):
                reference = match.group(1).strip().partition("|")[0].strip()
                reference_match = _REFERENCE_PATH_RE.fullmatch(reference)
                if reference_match is None:
                    findings.append("DP binding must name a node output field")
                    continue
                producer, raw_path = reference_match.groups()
                if producer not in refs:
                    findings.append("DP binding references an unknown node")
                    continue
                producer_outputs = nodes_by_ref[producer].get("output_schema", {}).get("properties")
                if "." in raw_path or "[" in raw_path or "]" in raw_path:
                    findings.append(
                        "DP binding must bind a declared top-level output field; "
                        "pass whole objects and inspect nested fields inside the DP"
                    )
                    continue
                output_field = raw_path
                if not isinstance(producer_outputs, dict) or output_field not in producer_outputs:
                    findings.append("DP binding references an undeclared output field")
                if producer == reference_id:
                    findings.append("DP binding references its own output")
                elif reference_id not in reachable(producer):
                    findings.append("DP binding references a node that is not upstream")

    if triggers:
        trigger_ref = triggers[0]["reference_id"]
        if reachable(trigger_ref) | {trigger_ref} != refs:
            findings.append("workflow is not fully reachable from its trigger")
    return findings


def _compile_summary(
    plan: dict,
    result: dict,
    *,
    candidate_digest: str | None,
) -> dict:
    workflow = result.get("workflow")
    data = workflow.get("data") if isinstance(workflow, dict) else None
    flows = data.get("flows") if isinstance(data, dict) else None
    flow = flows[0] if isinstance(flows, list) and flows and isinstance(flows[0], dict) else {}
    nodes = flow.get("nodes")
    edges = flow.get("edges")

    capability_ids: list[str] = []
    steps = plan.get("steps")
    if result.get("status") == "compiled" and isinstance(steps, list):
        for step in steps:
            capability_id = step.get("capsule_id") if isinstance(step, dict) else None
            if isinstance(capability_id, str) and capability_id not in capability_ids:
                capability_ids.append(capability_id)
            if len(capability_ids) == 20:
                break

    summary = {
        "status": result["status"],
        "findings": result["findings"],
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
        "edge_count": len(edges) if isinstance(edges, list) else 0,
        "capability_ids": capability_ids,
    }
    if candidate_digest is not None:
        summary["candidate_digest"] = candidate_digest
    return summary


def _write_atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
        temporary_path.replace(path)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", help="PlanIR JSON file (default: stdin)")
    ap.add_argument("--out", help="write compiled workflow JSON here")
    ap.add_argument(
        "--allow-html-node",
        action="store_true",
        help="allow HTML nodes with optional terminal URL delivery for a server-authorized turn",
    )
    args = ap.parse_args()
    plan = json.loads(Path(args.plan).read_text() if args.plan else sys.stdin.read())
    result = compile_plan(plan, allow_html_node=args.allow_html_node)
    workflow_bytes: bytes | None = None
    if result.get("workflow"):
        workflow_bytes = json.dumps(result["workflow"], indent=2).encode("utf-8")
        if args.out:
            _write_atomic_bytes(Path(args.out), workflow_bytes)
    candidate_digest = (
        "sha256:" + hashlib.sha256(workflow_bytes).hexdigest()
        if result["status"] == "compiled" and workflow_bytes is not None
        else None
    )
    print(
        json.dumps(
            _compile_summary(
                plan,
                result,
                candidate_digest=candidate_digest,
            )
        )
    )
    return 0 if result["status"] == "compiled" else 1


if __name__ == "__main__":
    raise SystemExit(main())
