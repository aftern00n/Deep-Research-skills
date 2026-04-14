---
name: research-deep
description: Read a research project, launch parallel deep-research tasks, and write validated JSON outputs per item.
---

# Research Deep - Deep Research

## Trigger
`/research-deep`

## Workflow

### Step 1: Locate the Project
Find `*/outline.yaml` under the current working directory.

If multiple candidates exist, ask the user which project directory to use.

Read from `outline.yaml`:
- `topic`
- `topic_slug`
- `project_dir`
- `items`
- `execution.batch_size`
- `execution.items_per_agent`
- `execution.output_dir`

Resolve:
- `project_dir`: absolute path from `outline.yaml`
- `fields_path`: `{project_dir}/fields.yaml`
- `output_dir`: resolve `execution.output_dir` relative to `project_dir` if needed
- `validator_path`: absolute path to the bundled validator script in this skill directory

### Step 2: Resume Check
- Create `output_dir` if missing
- Check completed JSON files in `output_dir`
- Skip completed items unless the user explicitly asks for regeneration

### Step 3: Batch Execution
- Execute in batches of `batch_size`
- Each agent handles `items_per_agent` items
- Use background parallel agents when possible
- Ask for user confirmation before starting the next batch only if the workload is large or the user asked for staged execution

**Hard Constraint**: Reproduce the following prompt exactly, only replacing variables in `{...}`.

```python
prompt = f"""## Task
Research {item_related_info}, output structured JSON to {output_path}

## Field Definitions
Read {fields_path} to get all field definitions

## Output Requirements
1. Output JSON according to fields defined in fields.yaml
2. Mark uncertain field values with [uncertain]
3. Add uncertain array at the end of JSON, listing all uncertain field names
4. Add references array at the end of JSON, listing the source links used for this item
5. Each references item must use the exact structure `{"label": "...", "url": "https://..."}`
6. All field values must be in English

## Output Path
{output_path}

## Validation
After completing JSON output, run validation script to ensure complete field coverage:
python {validator_path} -f {fields_path} -j {output_path}
Task is complete only after validation passes.
"""
```

### Step 4: Validation and Monitoring
- Run the validator after each JSON is produced
- Treat validation failure as task failure
- Show progress by completed item count and failed item names

### Step 5: Summary
After all items finish, report:
- Completion count
- Failed items
- Items containing uncertain values
- Output directory

## Output Contract
Each item writes one JSON file:

```text
{output_dir}/{item_name_slug}.json
```

Rules:
- `item_name_slug` should replace spaces with `_` and remove filesystem-hostile characters.
- JSON must cover every defined field when possible; if not, use `[uncertain]` and include the field name in `uncertain`.
- JSON should include a top-level `references` array for the source links used to produce the item report.
- `references` is the canonical source format for all newly generated outputs.
- Each reference object must contain:
  - `label`: short human-readable source name
  - `url`: absolute `http` or `https` link
- The validator script is the source of truth for schema coverage.

Example:

```json
{
  "name": "Example Item",
  "release_date": "2025-01-01",
  "uncertain": [],
  "references": [
    {
      "label": "Official announcement",
      "url": "https://example.com/announcement"
    },
    {
      "label": "Documentation",
      "url": "https://example.com/docs"
    }
  ]
}
```

## Agent Config
- Background execution: Yes
- Task output: Disabled when the agent writes the JSON file directly
- Resume support: Yes
