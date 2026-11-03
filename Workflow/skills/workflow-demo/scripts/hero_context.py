#!/usr/bin/env python3
"""Read only the selected on-menu hero and its pinned workflow definition."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERO_ROOT = Path(__file__).resolve().parents[3] / "hero-templates"
MANIFEST = HERO_ROOT / "manifest.json"
LIST_FIELDS = (
    "id",
    "title",
    "prompt",
    "license",
    "credit_cost",
    "credits_per_run",
    "requires_3p",
    "required_inputs",
)


def live_heroes(manifest: dict) -> dict:
    return {entry["id"]: entry for entry in manifest["templates"]
            if entry.get("on_menu") is True and entry.get("file")}


def live_shortcuts(manifest: dict) -> list[dict]:
    heroes = live_heroes(manifest)
    shortcuts = []
    for shortcut in manifest["shortcuts"]:
        if "destinations" in shortcut:
            destinations = [d for d in shortcut["destinations"] if d["template"] in heroes]
            if destinations:
                shortcuts.append({**shortcut, "destinations": destinations})
        elif shortcut["template"] in heroes:
            shortcuts.append(shortcut)
    return shortcuts


def shortcut_rows(manifest: dict, host: str) -> list[dict]:
    prefix = manifest["shortcut_prefix"][host]
    rows = []
    for shortcut in live_shortcuts(manifest):
        row = {
            "id": shortcut["id"],
            "shortcut_title": shortcut["title"],
            "shortcut_description": shortcut["description"],
            "shortcut_prompt": prefix + shortcut["suffix"],
            "cost": shortcut["cost"],
        }
        if "destinations" in shortcut:
            row["destinations"] = [d["name"] for d in shortcut["destinations"]]
        rows.append(row)
    if len({row["shortcut_prompt"].casefold() for row in rows}) != len(rows):
        raise ValueError("Expected distinct shortcut prompts")
    return rows


def menu_table(rows: list[dict]) -> str:
    def cell(text: str) -> str:
        return " ".join(text.split()).replace("|", "\\|")
    lines = ["| Hero scenario | Prompt | Cost (your first 10 runs are free, no license required) |", "|---|---|---|"]
    for row in rows:
        lines.append(f"| {cell(row['shortcut_description'])} | `{row['shortcut_prompt']}` | {cell(row['cost'])} |")
    return "\n".join(lines)


def match_shortcut(manifest: dict, host: str, message: str) -> dict:
    text = " ".join(message.split()).casefold()
    prefix = manifest["shortcut_prefix"][host].strip().casefold()
    if text.startswith(prefix + " "):
        text = text[len(prefix) + 1:]
    for shortcut in live_shortcuts(manifest):
        suffix = shortcut["suffix"].casefold()
        if "destinations" not in shortcut:
            if text == suffix:
                return {"shortcut": shortcut["id"], "template": shortcut["template"]}
            continue
        if text == suffix:
            return {"shortcut": shortcut["id"], "needs_destination": [d["name"] for d in shortcut["destinations"]]}
        for destination in shortcut["destinations"]:
            name = destination["name"].casefold()
            if text in (f"{suffix} to {name}", f"{suffix} {name}"):
                return {"shortcut": shortcut["id"], "template": destination["template"]}
    return {"shortcut": None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List only on-menu hero identifiers and selection fields")
    group.add_argument("--quick-menu", action="store_true", help="List the copyable shortcut prompts for the capability menu")
    group.add_argument("--match", metavar="MESSAGE", help="Resolve a user message to a shortcut and its template, or the destinations to ask about")
    group.add_argument("--id", help="Read one exact on-menu hero ID and its pinned template")
    parser.add_argument("--markdown", action="store_true", help="With --quick-menu, print the finished menu table")
    parser.add_argument("--out", type=Path, help="For --id, copy only the pinned workflow JSON to this file")
    parser.add_argument("--host", choices=("codex", "claude"), default="codex", help="Host syntax for --quick-menu and --match")
    args = parser.parse_args()
    if args.out is not None and args.id is None:
        parser.error("--out requires --id")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        heroes = list(live_heroes(manifest).values())
        if args.list:
            result = [{key: entry.get(key) for key in LIST_FIELDS} for entry in heroes]
        elif args.quick_menu:
            result = shortcut_rows(manifest, args.host)
            if args.markdown:
                print(menu_table(result))
                return 0
        elif args.match is not None:
            result = match_shortcut(manifest, args.host, args.match)
        else:
            matches = [entry for entry in heroes if entry.get("id") == args.id]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one on-menu hero with id {args.id!r}")
            entry = matches[0]
            filename = entry.get("file")
            if not isinstance(filename, str) or Path(filename).name != filename:
                raise ValueError("Hero manifest has an invalid template filename")
            template_path = HERO_ROOT / filename
            template_bytes = template_path.read_bytes()
            template = json.loads(template_bytes)
            if args.out is None:
                result = {"entry": entry, "template": template}
            else:
                output = args.out.expanduser().resolve()
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(template_bytes)
                result = {"entry": entry, "template_path": str(output)}
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
