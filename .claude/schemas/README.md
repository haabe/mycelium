# Schemas — Canvas Validation Schemas

JSON schemas for validating canvas YAML files. Used by `scripts/validate_canvas.py` and CI pipelines to ensure canvas files maintain structural integrity.

## Structure

- **[canvas/](canvas/)** — Per-file schemas matching each canvas YAML file (purpose.yml, opportunities.yml, etc.)

Schemas define required fields, allowed values, and structural constraints. They catch issues like missing `_meta` blocks, invalid confidence scores, or malformed evidence entries before they cause downstream problems.
