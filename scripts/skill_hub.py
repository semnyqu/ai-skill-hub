#!/usr/bin/env python3
"""Read-only local checks for the ai-skill-hub repository."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "skills.json"


def load_registry():
    with REGISTRY.open(encoding="utf-8") as stream:
        data = json.load(stream)
    names = [item["name"] for item in data["skills"]]
    if len(names) != len(set(names)):
        raise ValueError("registry contains duplicate skill names")
    return data


def validate(data):
    errors = []
    for item in data["skills"]:
        directory = ROOT / "skills" / item["name"]
        skill_file = directory / "SKILL.md"
        if not directory.is_dir():
            errors.append(f"{item['name']}: skill directory is missing")
            continue
        if not skill_file.is_file():
            errors.append(f"{item['name']}: SKILL.md is missing")
            continue
        content = skill_file.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.S)
        if not match:
            errors.append(f"{item['name']}: YAML frontmatter is missing")
        elif not re.search(r"(?m)^name:\s*[\"']?" + re.escape(item["name"]) + r"[\"']?\s*$", match.group(1)):
            errors.append(f"{item['name']}: frontmatter name does not match registry")
    return errors


def main():
    try:
        data = load_registry()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Registry error: {error}", file=sys.stderr)
        return 2
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    if command == "list":
        for item in data["skills"]:
            print(f"{item['name']}\t{item['version']}\t{item['category']}")
        return 0
    if command == "validate":
        errors = validate(data)
        if errors:
            print("Validation failed:")
            print("\n".join(f"- {error}" for error in errors))
            return 1
        print(f"Validated {len(data['skills'])} skills.")
        return 0
    print("Usage: python3 scripts/skill_hub.py [list|validate]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
