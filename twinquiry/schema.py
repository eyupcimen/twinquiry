"""Shared response contracts; validation needs only the standard library."""


def obj(fields):
    return {"type": "object", "additionalProperties": False,
            "properties": fields, "required": list(fields)}


TEXT = {"type": "string", "minLength": 1}


def array(items):
    return {"type": "array", "items": items}


ANSWER = obj({
    "summary": TEXT,
    "analysis": TEXT,
    "claims": array(obj({
        "claim": TEXT,
        "evidence": TEXT,
        "source_ids": array(TEXT),
        "status": {"type": "string", "enum": ["supported", "inference", "unverified"]},
    })),
    "open_questions": array(TEXT),
})

REVIEW = obj({
    "verdict": {"type": "string", "enum": ["APPROVE", "REVISE", "BLOCKED"]},
    "summary": TEXT,
    "strengths": array(TEXT),
    "findings": array(obj({
        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
        "issue": TEXT,
        "evidence": TEXT,
        "suggestion": TEXT,
    })),
    "limitations": array(TEXT),
})


def validate(value, schema, path="response"):
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["required"]):
            raise ValueError(f"{path}: expected exactly {schema['required']}")
        for key, child in schema["properties"].items():
            validate(value[key], child, f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected a list")
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]")
    elif kind == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: expected nonempty text")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: invalid choice {value!r}")


def check_response(value, stage, sources, web=False):
    validate(value, REVIEW if stage == "review" else ANSWER)
    if stage == "review":
        material = any(f["severity"] in ("high", "medium") for f in value["findings"])
        if value["verdict"] == "APPROVE" and material:
            raise ValueError("APPROVE cannot include unresolved high/medium findings")
        if value["verdict"] == "REVISE" and not value["findings"]:
            raise ValueError("REVISE requires concrete findings")
        if value["verdict"] == "BLOCKED" and not value["limitations"]:
            raise ValueError("BLOCKED requires a limitation")
    else:
        for claim in value["claims"]:
            if claim["status"] == "supported" and not claim["source_ids"]:
                raise ValueError("Supported claims need source IDs")
            for source in claim["source_ids"]:
                if source not in sources and not (web and source.startswith("https://")):
                    raise ValueError(f"Unknown source: {source}")
    return value
