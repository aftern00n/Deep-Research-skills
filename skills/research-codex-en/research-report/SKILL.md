---
name: research-report
description: Render a markdown report from deep-research JSON results using the bundled report generator.
---

# Research Report - Summary Report

## Trigger
`/research-report`

## Workflow

### Step 1: Locate the Project
Find `*/outline.yaml` under the current working directory.

If multiple projects exist, ask the user which one to render.

Read:
- `topic`
- `project_dir`
- `execution.output_dir`

Resolve `output_dir` relative to `project_dir` if it is not already absolute.

### Step 2: Choose TOC Summary Fields
Read all JSON files in `output_dir` and collect short candidate fields suitable for the table of contents, for example:
- `release_date`
- `github_stars`
- `valuation`
- `user_scale`
- `score`

Ask the user which fields to show next to each item name.

### Step 3: Run the Bundled Report Generator
Use the bundled script in this skill directory:

```text
research-report/generate_report.py
```

Run it with:
- `--project-dir {project_dir}`
- optional repeated `--summary-field <field_name>`

The script must:
- Read `outline.yaml`, `fields.yaml`, and all JSON files from `output_dir`
- Support both flat JSON and nested category JSON
- Skip values containing `[uncertain]`
- Skip fields named in the JSON `uncertain` array
- Render `report.md` into `{project_dir}/report.md`

### Step 4: Confirm Output
Show:
- Item count rendered
- Output path
- Any items skipped due to missing JSON

## Bundled Generator Requirements
The generator already handles:
- Category alias mapping between human-readable names and JSON keys
- Recursive formatting for dicts and lists
- Collection of extra fields into `Other Info`
- Filtering of uncertain values

## Output
- `{project_dir}/report.md` - summary report
