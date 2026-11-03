"""Lexical capsule prefilter: intent -> top DP-capsule candidates from dp_capsule_catalog.json.

Deliberately NOT a semantic/ES search (Phase 1 has none). It narrows the small bundled capsule
catalog by token overlap so the planning agent makes the final choice from a short list -- the
model is the selector, this just prefilters. Prints JSON candidates (or an empty list -> the agent
routes the step to a full DP).

    python3 select_skill.py "summarize the meeting and email the participants"
    python3 select_skill.py "<intent>" --top 5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SKILL_DIR = Path(__file__).resolve().parents[1]
CAPSULE_CATALOG = SKILL_DIR / "resources" / "dp_capsule_catalog.json"

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "with",
    "from",
    "into",
    "this",
    "that",
    "it",
    "is",
    "are",
    "be",
    "as",
    "by",
    "at",
    "then",
    "when",
    "after",
    "my",
    "me",
    "our",
    "use",
    "using",
    "via",
    "based",
    "please",
    "user",
    "users",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 2}


def _normalized_phrase(text: str) -> str:
    return " ".join(_TOKEN_RE.findall((text or "").lower()))


def rank(
    intent: str,
    capsules: list[dict],
    top: int,
    required_apps: set[str] | None = None,
) -> list[dict]:
    q = _tokens(intent)
    normalized_intent = _normalized_phrase(intent)
    required_apps = required_apps or set()
    scored = []
    for c in capsules:
        incompatible_phrases = c.get("incompatible_intent_phrases") or []
        if any(
            isinstance(phrase, str)
            and bool(_normalized_phrase(phrase))
            and f" {_normalized_phrase(phrase)} " in f" {normalized_intent} "
            for phrase in incompatible_phrases
        ):
            continue
        app_scope = set(c.get("app_scope") or [])
        if not required_apps <= app_scope:
            continue
        name_doc = _tokens(c.get("capsule_id", "").replace("_", " ").replace("-", " "))
        doc = name_doc | _tokens(c.get("when_to_use", ""))
        overlap = q & doc
        if not overlap:
            continue
        name_overlap = q & name_doc
        exact_app_scope = bool(required_apps) and app_scope == required_apps
        score = (
            len(overlap)
            + (2 * len(name_overlap))
            + (len(overlap) / max(len(q), 1))
            + (2 if exact_app_scope else 0)
        )
        scored.append(
            (
                score,
                {
                    "capsule_id": c["capsule_id"],
                    "when_to_use": c.get("when_to_use", ""),
                    "app_scope": c.get("app_scope", []),
                    "typed_outputs": c.get("typed_outputs", []),
                    "downstream_contract": c.get("downstream_contract", {}),
                    "entry_gate_contract": c.get("entry_gate_contract", {}),
                    "body_bytes": c.get("body_bytes", 0),
                    "matched_count": len(overlap),
                    "name_matched_count": len(name_overlap),
                },
            )
        )
    scored.sort(key=lambda s: s[0], reverse=True)
    return [c for _, c in scored[:top]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("intent", help="the step's natural-language intent")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument(
        "--required-app",
        action="append",
        default=[],
        help="canonical app key required by this step; repeat for every required app",
    )
    args = ap.parse_args()
    if not _tokens(args.intent):
        print(
            "select_skill: the intent produced no searchable terms. This selector matches "
            "ASCII keywords only -- write intent in English. This is NOT a 'no capsule "
            "matched' result; do not fall back to full_dp on this error.",
            file=sys.stderr,
        )
        return 2
    capsules = json.loads(CAPSULE_CATALOG.read_text())["capsules"]
    candidates = rank(args.intent, capsules, args.top, set(args.required_app))
    print(json.dumps({"candidates": candidates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
