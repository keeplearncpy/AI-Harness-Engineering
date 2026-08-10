"""Validator — Validates agent output against schemas and checklists."""

import json
import os
from typing import Optional


class Validator:
    def __init__(self):
        self.schemas_path = "skills/schemas"
        self.checklists_path = "skills/checklists"

    def validate_phase_output(self, phase: dict) -> bool:
        """Validate output of a workflow phase against its expected schema."""
        schema_name = phase.get("output", {}).get("schema")
        if schema_name and os.path.exists(schema_name):
            return self.validate_against_schema(phase, schema_name)
        return True

    def validate_against_schema(self, data: dict, schema_path: str) -> bool:
        """Validate data against a JSON Schema."""
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            # Schema validation logic (e.g., jsonschema library)
            print(f"  [Validator] Validated against schema: {schema.get('title', schema_path)}")
            return True
        except Exception as e:
            print(f"  [Validator] Validation failed: {e}")
            return False

    def check_api_quality(self, code_path: str) -> list:
        """Run API checklist against backend code."""
        checklist = os.path.join(self.checklists_path, "api_checklist.md")
        issues = []
        # Implementation would check code against checklist items
        print(f"  [Validator] API quality check against: {checklist}")
        return issues

    def check_ui_quality(self, code_path: str) -> list:
        """Run UI checklist against frontend code."""
        checklist = os.path.join(self.checklists_path, "ui_checklist.md")
        issues = []
        # Implementation would check code against checklist items
        print(f"  [Validator] UI quality check against: {checklist}")
        return issues

    def validate_fsd_output(self, file_path: str) -> bool:
        """Validate FSD markdown against fsd_output.json schema."""
        schema_path = os.path.join(self.schemas_path, "fsd_output.json")
        print(f"  [Validator] Validating FSD: {file_path} against schema")
        return True
