#!/usr/bin/env python3

import json
import sys
from collections import defaultdict
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


def load_fields_yaml(fields_path):
    with fields_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    raw_categories = data.get("field_categories")
    if raw_categories is None:
        raw_categories = data.get("categories", [])

    items = []
    for category in raw_categories or []:
        category_name = category.get("category") or category.get("name") or "Unknown"
        for field in category.get("fields", []) or []:
            field_name = field.get("name")
            if not field_name:
                continue
            items.append((field_name, category_name, field.get("required", False)))

    all_fields = {name for name, _, _ in items}
    required_fields = {name for name, _, required in items if required}
    field_categories = {name: category for name, category, _ in items}
    return all_fields, required_fields, field_categories


def category_aliases():
    aliases = set()
    for canonical, values in CATEGORY_MAPPING.items():
        aliases.add(canonical)
        aliases.update(values)
    return aliases


def extract_json_fields(data, nested_keys=None):
    nested_keys = category_aliases() if nested_keys is None else nested_keys
    fields = set()

    def walk(obj, allow_container_skip):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in SKIP_KEYS:
                    continue
                if allow_container_skip and key in nested_keys and isinstance(value, dict):
                    walk(value, True)
                    continue
                fields.add(key)
                walk(value, False)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, False)

    walk(data, True)
    return fields


def validate_json(json_path, all_fields, required_fields, field_categories, min_coverage):
    with json_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    json_fields = extract_json_fields(data)
    covered = all_fields & json_fields
    missing = all_fields - json_fields
    extra = json_fields - all_fields
    missing_required = missing & required_fields

    missing_by_category = defaultdict(list)
    for field in missing:
        missing_by_category[field_categories.get(field, "Unknown")].append(field)

    coverage_rate = len(covered) / len(all_fields) * 100 if all_fields else 100.0
    valid = not missing_required and coverage_rate >= min_coverage

    return {
        "file": json_path.name,
        "total_defined": len(all_fields),
        "covered": len(covered),
        "missing": len(missing),
        "extra": len(extra),
        "coverage_rate": coverage_rate,
        "missing_required": sorted(missing_required),
        "missing_optional": sorted(missing - required_fields),
        "missing_by_category": {k: sorted(v) for k, v in missing_by_category.items()},
        "extra_fields": sorted(extra),
        "valid": valid,
        "min_coverage": min_coverage,
    }


def print_result(result, verbose=True):
    status = "PASS" if result["valid"] else "FAIL"
    line = "=" * 60
    print(f"\n{line}")
    print(f"[{status}] {result['file']}")
    print(line)
    print(
        f"Coverage: {result['coverage_rate']:.1f}% "
        f"({result['covered']}/{result['total_defined']}, required minimum: {result['min_coverage']:.1f}%)"
    )
    if result["missing_required"]:
        print(f"\n[ERROR] Missing required fields ({len(result['missing_required'])}):")
        print("\n".join(f"  - {field}" for field in result["missing_required"]))
    if not result["valid"] and result["coverage_rate"] < result["min_coverage"]:
        print(
            f"\n[ERROR] Coverage below threshold: "
            f"{result['coverage_rate']:.1f}% < {result['min_coverage']:.1f}%"
        )
    if verbose and result["missing_optional"]:
        missing_required = set(result["missing_required"])
        print(f"\n[WARN] Missing optional fields ({len(result['missing_optional'])}):")
        for category in sorted(result["missing_by_category"]):
            optional = [field for field in result["missing_by_category"][category] if field not in missing_required]
            if optional:
                print(f"  [{category}]: {', '.join(optional)}")
    if verbose and result["extra_fields"]:
        extra = result["extra_fields"]
        print(f"\n[INFO] Extra fields ({len(extra)}):")
        print(f"  {', '.join(extra[:10])}")
        if len(extra) > 10:
            print(f"  ... and {len(extra) - 10} more")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate whether JSON files cover all fields defined in fields.yaml")
    parser.add_argument("--fields", "-f", type=str, help="Path to fields.yaml", default="fields.yaml")
    parser.add_argument("--json", "-j", type=str, nargs="*", help="JSON file paths to validate")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing JSON files", default="results")
    parser.add_argument("--quiet", "-q", action="store_true", help="Show summary only")
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=100.0,
        help="Minimum coverage percentage required to pass validation (default: 100)",
    )
    args = parser.parse_args()

    fields_path = Path(args.fields)
    if not fields_path.exists():
        for candidate in (Path.cwd() / "fields.yaml", Path.cwd().parent / "fields.yaml"):
            if candidate.exists():
                fields_path = candidate
                break
    if not fields_path.exists():
        print(f"[ERROR] fields.yaml not found: {fields_path}")
        sys.exit(1)

    print(f"Field definition file: {fields_path}")
    all_fields, required_fields, field_categories = load_fields_yaml(fields_path)
    print(
        f"Total fields: {len(all_fields)} "
        f"(required: {len(required_fields)}, optional: {len(all_fields) - len(required_fields)})"
    )

    json_files = (
        [Path(path) for path in args.json]
        if args.json
        else sorted(Path(args.dir).glob("*.json")) if Path(args.dir).exists() else []
    )
    if not json_files:
        print("[WARN] No JSON files found")
        sys.exit(0)

    results = []
    for json_path in json_files:
        if not json_path.exists():
            print(f"[WARN] File not found: {json_path}")
            continue
        result = validate_json(
            json_path=json_path,
            all_fields=all_fields,
            required_fields=required_fields,
            field_categories=field_categories,
            min_coverage=args.min_coverage,
        )
        results.append(result)
        print_result(result, verbose=not args.quiet)

    line = "=" * 60
    print(f"\n{line}")
    print("Summary")
    print(line)
    passed = sum(1 for result in results if result["valid"])
    avg_coverage = sum(result["coverage_rate"] for result in results) / len(results) if results else 0
    print(f"Validation passed: {passed}/{len(results)}")
    print(f"Average coverage: {avg_coverage:.1f}%")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
