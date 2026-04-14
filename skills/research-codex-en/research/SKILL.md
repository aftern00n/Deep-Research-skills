---
name: research
description: Conduct preliminary research on a topic and generate a reusable project outline for deep research and reporting.
---

# Research Skill - Preliminary Research

## Trigger
`/research <topic>`

## Goal
Create a self-contained research project directory that later steps can execute without guessing schemas or paths.

## Workflow

### Step 1: Generate Initial Framework from Model Knowledge
Based on the topic, use model knowledge to draft:
- Main research objects/items in this domain
- Suggested field framework for later structured collection

Show the draft to the user and confirm:
- Whether any items should be added or removed
- Whether the field framework is sufficient

### Step 2: Web Search Supplement
Ask the user for a time range (for example: last 6 months, since 2024, unlimited).

Launch 1 background web-search agent to supplement the initial framework.

**Hard Constraint**: Reproduce the following prompt exactly, only replacing variables in `{...}`.

```python
prompt = f"""## Task
Research topic: {topic}
Current date: {YYYY-MM-DD}

Based on the following initial framework, supplement latest items and recommended research fields.

## Existing Framework
{step1_output}

## Goals
1. Verify if existing items are missing important objects
2. Supplement items based on missing objects
3. Continue searching for {topic} related items within {time_range} and supplement
4. Supplement new fields

## Output Requirements
Return structured results directly (do not write files):

### Supplementary Items
- item_name: Brief explanation (why it should be added)
...

### Recommended Supplementary Fields
- field_name: Field description (why this dimension is needed)
...

### Sources
- [Source1](url1)
- [Source2](url2)
"""
```

### Step 3: Ask User for Existing Fields
Ask whether the user already has a field definition file. If yes, read it and merge it into the final schema.

### Step 4: Generate Project Files
Merge the initial framework, web supplement, and any user-provided fields into a project directory:

`./{topic_slug}/`

Create:
- `outline.yaml`
- `fields.yaml`
- `results/` directory

### Step 5: Show and Confirm
Present the generated paths and summarize:
- Topic
- Item count
- Field count
- Execution settings

## Required File Contracts

### `outline.yaml`
Must use this structure:

```yaml
topic: Example Topic
topic_slug: example-topic
project_dir: /absolute/path/to/example-topic
items:
  - name: Example Item
    category: Example Category
    description: Short explanation
execution:
  batch_size: 3
  items_per_agent: 1
  output_dir: ./results
```

Rules:
- `topic_slug` must be filesystem-safe and match the created directory name.
- `project_dir` must be an absolute path to the project directory.
- `execution.output_dir` may be relative, but it is always resolved relative to `project_dir`.

### `fields.yaml`
Must use this structure:

```yaml
field_categories:
  - category: Basic Info
    fields:
      - name: name
        description: Item name
        detail_level: brief
        required: true
      - name: release_date
        description: Public release date
        detail_level: moderate
        required: false
uncertain: []
```

Rules:
- Top-level key must be `field_categories`.
- Each category entry must use the key `category`.
- Each field entry must include `name`, `description`, and `detail_level`.
- `required` is optional but recommended. If omitted, it defaults to `false`.
- Reserve top-level `uncertain` for later deep-research output; keep it as an empty list here.

## Output Path
```text
{current_working_directory}/{topic_slug}/
  ├── outline.yaml
  ├── fields.yaml
  └── results/
```

## Follow-up Commands
- `/research-add-items` - supplement items in `outline.yaml`
- `/research-add-fields` - supplement fields in `fields.yaml`
- `/research-deep` - collect structured JSON results for each item
- `/research-report` - render `report.md` from JSON results
