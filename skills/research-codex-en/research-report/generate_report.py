#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path

import yaml

CATEGORY_MAPPING = {
    "Basic Info": ["basic_info", "Basic Info"],
    "Technical Features": ["technical_features", "technical_characteristics", "Technical Features"],
    "Performance Metrics": ["performance_metrics", "performance", "Performance Metrics"],
    "Milestone Significance": ["milestone_significance", "milestones", "Milestone Significance"],
    "Business Info": ["business_info", "commercial_info", "Business Info"],
    "Competition & Ecosystem": ["competition_ecosystem", "competition", "Competition & Ecosystem", "Competition Ecosystem"],
    "History": ["history", "History"],
    "Market Positioning": ["market_positioning", "market", "Market Positioning"],
}

SKIP_KEYS = {"_source_file", "uncertain"}


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "item"


def load_yaml(path):
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_field_categories(fields_data):
    categories = fields_data.get("field_categories") or []
    return [
        {
            "category": category.get("category") or "Uncategorized",
            "fields": category.get("fields") or [],
        }
        for category in categories
    ]


def category_aliases(category_name):
    aliases = {category_name}
    aliases.update(CATEGORY_MAPPING.get(category_name, []))
    for canonical, values in CATEGORY_MAPPING.items():
        if category_name in values:
            aliases.add(canonical)
            aliases.update(values)
    return aliases


def lookup_field(data, field_name, category_name=None):
    if isinstance(data, dict):
        if field_name in data:
            return data[field_name]

        if category_name:
            for alias in category_aliases(category_name):
                nested = data.get(alias)
                if isinstance(nested, dict) and field_name in nested:
                    return nested[field_name]

        for value in data.values():
            result = lookup_field(value, field_name, None)
            if result is not None:
                return result

    if isinstance(data, list):
        for item in data:
            result = lookup_field(item, field_name, category_name)
            if result is not None:
                return result

    return None


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.replace("\n", "<br>") if len(value) > 100 else value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(item, dict) for item in value):
            lines = []
            for item in value:
                parts = [f"{key}: {format_value(val)}" for key, val in item.items() if format_value(val)]
                if parts:
                    lines.append(" | ".join(parts))
            return "<br>".join(lines)
        parts = [format_value(item) for item in value if format_value(item)]
        if len(parts) <= 3:
            return ", ".join(parts)
        return "<br>".join(parts)
    if isinstance(value, dict):
        parts = [f"{key}: {format_value(val)}" for key, val in value.items() if format_value(val)]
        return "<br>".join(parts)
    return str(value)


def contains_uncertain(value):
    if isinstance(value, str):
        return "[uncertain]" in value
    if isinstance(value, list):
        return any(contains_uncertain(item) for item in value)
    if isinstance(value, dict):
        return any(contains_uncertain(item) for item in value.values())
    return False


def iter_extra_fields(data, category_roots):
    extras = {}

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in SKIP_KEYS:
                    continue
                if key in category_roots and isinstance(value, dict):
                    walk(value)
                    continue
                if isinstance(value, (dict, list)):
                    walk(value)
                else:
                    extras.setdefault(key, value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return extras


def main():
    parser = argparse.ArgumentParser(description="Generate a markdown report from research JSON results.")
    parser.add_argument("--project-dir", required=True, help="Absolute or relative path to the research project directory")
    parser.add_argument("--summary-field", action="append", default=[], help="Field to show in the report TOC")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    outline_path = project_dir / "outline.yaml"
    fields_path = project_dir / "fields.yaml"
    report_path = project_dir / "report.md"

    outline = load_yaml(outline_path)
    fields_data = load_yaml(fields_path)
    field_categories = load_field_categories(fields_data)
    defined_fields = {
        field["name"]
        for category in field_categories
        for field in category.get("fields", [])
        if field.get("name")
    }

    output_dir_raw = ((outline.get("execution") or {}).get("output_dir")) or "./results"
    output_dir = Path(output_dir_raw)
    if not output_dir.is_absolute():
        output_dir = (project_dir / output_dir).resolve()

    category_roots = {
        alias
        for category in field_categories
        for alias in category_aliases(category["category"])
    }

    json_paths = sorted(output_dir.glob("*.json"))
    items = []
    for json_path in json_paths:
        with json_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        items.append((json_path, data))

    lines = []
    topic = outline.get("topic") or project_dir.name
    lines.append(f"# {topic}")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")

    for index, (_, data) in enumerate(items, start=1):
        name = lookup_field(data, "name", "Basic Info") or data.get("name") or f"Item {index}"
        summary_parts = []
        for field_name in args.summary_field:
            value = lookup_field(data, field_name)
            if value in (None, "", []):
                continue
            if field_name in (data.get("uncertain") or []) or contains_uncertain(value):
                continue
            summary_parts.append(f"{field_name}: {format_value(value)}")
        suffix = f" - {' | '.join(summary_parts)}" if summary_parts else ""
        lines.append(f"{index}. [{name}](#{slugify(str(name))}){suffix}")

    if not items:
        lines.append("No JSON results found.")

    lines.append("")

    for index, (json_path, data) in enumerate(items, start=1):
        name = lookup_field(data, "name", "Basic Info") or data.get("name") or f"Item {index}"
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"_Source: {json_path.name}_")
        lines.append("")

        uncertain_fields = set(data.get("uncertain") or [])

        for category in field_categories:
            category_name = category["category"]
            rendered = []
            for field in category.get("fields", []):
                field_name = field.get("name")
                if not field_name or field_name in uncertain_fields:
                    continue
                value = lookup_field(data, field_name, category_name)
                if value in (None, "", []):
                    continue
                if contains_uncertain(value):
                    continue
                rendered.append((field_name, format_value(value)))

            if rendered:
                lines.append(f"### {category_name}")
                lines.append("")
                for field_name, value in rendered:
                    lines.append(f"- **{field_name}**: {value}")
                lines.append("")

        extra_fields = iter_extra_fields(data, category_roots)
        extra_fields = {
            key: value
            for key, value in extra_fields.items()
            if key not in defined_fields and key not in uncertain_fields and not contains_uncertain(value)
        }
        if extra_fields:
            lines.append("### Other Info")
            lines.append("")
            for key, value in sorted(extra_fields.items()):
                formatted = format_value(value)
                if formatted:
                    lines.append(f"- **{key}**: {formatted}")
            lines.append("")

        if uncertain_fields:
            lines.append("### Uncertain")
            lines.append("")
            for field_name in sorted(uncertain_fields):
                lines.append(f"- {field_name}")
            lines.append("")

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
