import os
import yaml
from typing import List, Union
from pydantic import ValidationError
from backend.app.models.sop import SOP


class SOPValidationError(Exception):
    """Raised when SOP YAML configuration is invalid or malformed."""
    pass


class SOPLoader:
    """
    Loader and validator for SOP YAML configurations.
    Enforces strict Pydantic model validation and duplicate ID detection.
    """

    @staticmethod
    def load_from_file(filepath: str) -> List[SOP]:
        if not os.path.exists(filepath):
            raise SOPValidationError(f"SOP configuration file not found at path: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            raise SOPValidationError(f"Error reading SOP file '{filepath}': {exc}") from exc

        return SOPLoader.load_from_yaml_string(content)

    @staticmethod
    def load_from_yaml_string(yaml_content: str) -> List[SOP]:
        if not yaml_content or not yaml_content.strip():
            raise SOPValidationError("SOP YAML content is empty.")

        try:
            data = yaml.safe_load(yaml_content)
        except Exception as exc:
            raise SOPValidationError(f"Malformed YAML syntax: {exc}") from exc

        if not isinstance(data, dict):
            raise SOPValidationError("Root SOP YAML content must be a dictionary.")

        if "sops" not in data or not isinstance(data["sops"], list):
            raise SOPValidationError("YAML root must contain a 'sops' list key.")

        sops_raw = data["sops"]
        if len(sops_raw) == 0:
            raise SOPValidationError("'sops' list cannot be empty.")

        sops: List[SOP] = []
        seen_ids = set()

        for idx, item in enumerate(sops_raw):
            if not isinstance(item, dict):
                raise SOPValidationError(f"SOP item at index {idx} is not a dictionary.")

            sop_id = item.get("id")
            if not sop_id or not str(sop_id).strip():
                raise SOPValidationError(f"SOP item at index {idx} is missing required 'id'.")

            sop_id_str = str(sop_id).strip()
            if sop_id_str in seen_ids:
                raise SOPValidationError(f"Duplicate SOP ID detected: '{sop_id_str}' at index {idx}.")

            try:
                sop_obj = SOP(**item)
            except ValidationError as ve:
                raise SOPValidationError(f"SOP ID '{sop_id_str}' validation failed: {ve}") from ve

            seen_ids.add(sop_id_str)
            sops.append(sop_obj)

        return sops
