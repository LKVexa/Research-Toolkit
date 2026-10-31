"""Paired descriptive loss comparison. No intervals, tests, or independence claim."""
from __future__ import annotations
import math
from numerical.data import NumericalError, MAX_PREDICTION, fields, identifier, number


def _index(rows, field, maximum):
    if not isinstance(rows, list) or not 4 <= len(rows) <= 248:
        raise NumericalError("Final arrays require 4 to 248 rows.")
    result = {}
    for row in rows:
        fields(row, ("id", field))
        row_id = identifier(row["id"])
        if row_id in result:
            raise NumericalError("Duplicate final row ID.")
        result[row_id] = number(row[field], maximum)
    return result


def compare(raw_predictions, final_labels, metric, direction="minimize", tolerance=1e-9):
    """Compare {candidate:[{id,value}], baseline:[{id,value}]} against [{id,y}]."""
    fields(raw_predictions, ("candidate", "baseline"))
    if metric not in ("mse", "mae") or direction not in ("minimize", "maximize"):
        raise NumericalError("Unsupported metric or declared direction.")
    tolerance = number(tolerance, 1e24)
    if tolerance < 0:
        raise NumericalError("Absolute tolerance cannot be negative.")
    labels = _index(final_labels, "y", 1e6)
    candidate = _index(raw_predictions["candidate"], "value", MAX_PREDICTION)
    baseline = _index(raw_predictions["baseline"], "value", MAX_PREDICTION)
    if set(labels) != set(candidate) or set(labels) != set(baseline):
        raise NumericalError("Prediction IDs must exactly match final-label IDs.")
    rows = []
    for row_id in sorted(labels):
        c = abs(candidate[row_id] - labels[row_id]); b = abs(baseline[row_id] - labels[row_id])
        if metric == "mse":
            c *= c; b *= b
        improvement = b - c if direction == "minimize" else c - b
        rows.append({"id": row_id, "candidate_loss": c, "baseline_loss": b,
                     "directional_improvement": improvement})
    n = len(rows)
    candidate_score = math.fsum(r["candidate_loss"] for r in rows) / n
    baseline_score = math.fsum(r["baseline_loss"] for r in rows) / n
    differences = [r["directional_improvement"] for r in rows]
    mean = math.fsum(differences) / n
    sd = math.sqrt(math.fsum((d - mean) ** 2 for d in differences) / n)
    result = "positive" if mean > tolerance else "negative" if mean < -tolerance else "inconclusive"
    return {"schema_version": "1.0.0", "metric": metric, "direction": direction,
            "tolerance": tolerance, "result": result, "candidate_score": candidate_score,
            "baseline_score": baseline_score, "mean_improvement": mean,
            "paired_differences": {"count": n, "mean": mean, "population_sd": sd,
                                   "min": min(differences), "max": max(differences)},
            "per_row": rows, "inference": "descriptive_only",
            "independence_claim": False, "stochastic_repeats": 0}
