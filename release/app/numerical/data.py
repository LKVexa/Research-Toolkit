"""Strict bounded data contracts and explicit removal of final outcomes."""
from __future__ import annotations
import math
import re

METHODS = ("ordinary-least-squares", "mean-baseline", "zero-predictor", "same-baseline")
MAX_ROWS = 256
MAX_VALUE = 1_000_000
MAX_PREDICTION = 1_000_000_000_000
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class NumericalError(ValueError):
    pass


def number(value, maximum=MAX_VALUE):
    if type(value) not in (int, float):
        raise NumericalError("Expected a finite bounded number; booleans are not numeric inputs.")
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as exc:
        raise NumericalError("Expected a finite bounded number.") from exc
    if not math.isfinite(normalized) or abs(normalized) > maximum:
        raise NumericalError("Expected a finite bounded number; booleans are not numeric inputs.")
    return normalized


def identifier(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise NumericalError("IDs and groups must be simple identifiers of 1 to 64 characters.")
    return value


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise NumericalError("Object fields do not match the fixed contract.")


def validate_dataset(value):
    """Return a fresh normalized dataset. One row per unique group is required."""
    fields(value, ("schema_version", "dataset_id", "license", "rows"))
    if value["schema_version"] != "1.0.0":
        raise NumericalError("Unsupported dataset schema version.")
    dataset_id = identifier(value["dataset_id"])
    license_text = value["license"]
    if not isinstance(license_text, str) or not license_text.strip() or len(license_text.encode("utf-8")) > 1024 or any(ord(c) < 32 for c in license_text):
        raise NumericalError("License must be nonempty single-line text of at most 1,024 UTF-8 bytes.")
    source = value["rows"]
    if not isinstance(source, list) or not 12 <= len(source) <= MAX_ROWS:
        raise NumericalError("Dataset requires 12 to 256 rows.")
    rows, seen_ids, seen_groups = [], set(), set()
    counts = {"development": 0, "final": 0}
    for item in source:
        fields(item, ("id", "group", "split", "x", "y"))
        row_id, group = identifier(item["id"]), identifier(item["group"])
        if row_id in seen_ids:
            raise NumericalError("Duplicate row ID.")
        if group in seen_groups:
            raise NumericalError("Duplicate group; one row per group and no cross-split group overlap are required.")
        split = item["split"]
        if not isinstance(split, str) or split not in counts:
            raise NumericalError("Split must be development or final.")
        counts[split] += 1
        seen_ids.add(row_id); seen_groups.add(group)
        rows.append({"id": row_id, "group": group, "split": split,
                     "x": number(item["x"]), "y": number(item["y"])})
    if counts["development"] < 8 or counts["final"] < 4:
        raise NumericalError("At least 8 development and 4 final rows are required.")
    return {"schema_version": "1.0.0", "dataset_id": dataset_id,
            "license": license_text, "rows": rows}


def make_request(dataset, method):
    """Only development labels enter the adapter. Metadata is never instructions."""
    dataset = validate_dataset(dataset)
    if method not in METHODS:
        raise NumericalError("Unknown fixed method.")
    return {"schema_version": "1.0.0", "method": method,
            "dev": [{"id": r["id"], "x": r["x"], "y": r["y"]}
                    for r in dataset["rows"] if r["split"] == "development"],
            "final": [{"id": r["id"], "x": r["x"]}
                      for r in dataset["rows"] if r["split"] == "final"]}


def final_labels(dataset):
    dataset = validate_dataset(dataset)
    return [{"id": r["id"], "y": r["y"]} for r in dataset["rows"] if r["split"] == "final"]


def validate_request(value):
    fields(value, ("schema_version", "method", "dev", "final"))
    if value["schema_version"] != "1.0.0" or value["method"] not in METHODS:
        raise NumericalError("Unsupported request version or fixed method.")
    dev, final = value["dev"], value["final"]
    if not isinstance(dev, list) or not isinstance(final, list) or len(dev) < 8 or len(final) < 4 or len(dev)+len(final) > MAX_ROWS:
        raise NumericalError("Request requires at least 8 development and 4 final rows, at most 256 total.")
    result = {"schema_version": "1.0.0", "method": value["method"], "dev": [], "final": []}
    seen = set()
    for split in ("dev", "final"):
        for row in value[split]:
            fields(row, ("id", "x", "y") if split == "dev" else ("id", "x"))
            row_id = identifier(row["id"])
            if row_id in seen:
                raise NumericalError("Duplicate request row ID.")
            seen.add(row_id)
            item = {"id": row_id, "x": number(row["x"])}
            if split == "dev":
                item["y"] = number(row["y"])
            result[split].append(item)
    return result
