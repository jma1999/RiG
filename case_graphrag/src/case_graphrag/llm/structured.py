from __future__ import annotations
from typing import Any
import json

from .client import client, MODEL


def _enforce_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema

    # Recurse into defs first
    for key in ("$defs", "definitions"):
        if key in schema and isinstance(schema[key], dict):
            for _, sub_schema in schema[key].items():
                _enforce_openai_strict_schema(sub_schema)

    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema and isinstance(schema[key], list):
            for sub_schema in schema[key]:
                _enforce_openai_strict_schema(sub_schema)

    if schema.get("type") == "array" and "items" in schema:
        _enforce_openai_strict_schema(schema["items"])

    if schema.get("type") == "object":
        properties = schema.get("properties", {})

        for _, prop_schema in properties.items():
            _enforce_openai_strict_schema(prop_schema)

        schema["additionalProperties"] = False
        schema["required"] = list(properties.keys())

    return schema


def call_structured(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    strict_schema = _enforce_openai_strict_schema(schema)

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": strict_schema,
                "strict": True,
            }
        },
    )

    if not response.output_text:
        raise ValueError("Structured output response had no output_text.")

    return json.loads(response.output_text)