"""Fixed deterministic methods. No network, dynamic code, or final-label input."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from numerical.data import NumericalError, MAX_PREDICTION, number, validate_request

MAX_REQUEST_BYTES = 131072


def predict(request):
    request = validate_request(request)
    method, dev = request["method"], request["dev"]
    x_mean = math.fsum(r["x"] for r in dev) / len(dev)
    y_mean = math.fsum(r["y"] for r in dev) / len(dev)
    slope, intercept, degenerate = 0.0, y_mean, False
    if method == "ordinary-least-squares":
        scale = max(abs(r["x"] - x_mean) for r in dev)
        if scale == 0:
            # The slope is unidentifiable. The fixed minimum-slope tie-break is
            # slope zero, yielding the development mean and no tuning parameter.
            degenerate = True
        else:
            z = [(r["x"] - x_mean) / scale for r in dev]
            denominator = math.fsum(v * v for v in z)
            beta = math.fsum(v * (r["y"] - y_mean) for v, r in zip(z, dev)) / denominator
            slope = number(beta / scale, MAX_PREDICTION)
            intercept = number(y_mean - slope * x_mean, MAX_PREDICTION)
    elif method == "zero-predictor":
        intercept = 0.0
    # mean-baseline and same-baseline intentionally use exactly the same rule.
    predictions = [{"id": r["id"], "value": number(slope * r["x"] + intercept, MAX_PREDICTION)}
                   for r in request["final"]]
    return {"schema_version": "1.0.0", "method": method, "predictions": predictions,
            "fit_details": {"training_rows": len(dev), "slope": slope, "intercept": intercept,
                            "development_x_mean": x_mean, "development_y_mean": y_mean,
                            "degenerate_development_x": degenerate,
                            "fitted_on": "development_only", "final_labels_received": False,
                            "stochastic": False, "tuned_parameters": 0}}


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise NumericalError("Duplicate JSON object field.")
            result[key] = value
        return result
    def invalid_constant(_):
        raise NumericalError("Non-finite JSON constant.")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fixed authored numerical diagnostic adapter")
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        path = Path(args.request).absolute()
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
                raise NumericalError("Linked request paths are unsupported.")
        with path.open("rb") as source:
            raw = source.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise NumericalError("Request exceeds 131,072 bytes.")
        result = predict(strict_json(raw.decode("utf-8")))
        print(json.dumps(result, allow_nan=False, separators=(",", ":")))
        return 0
    except (NumericalError, ValueError, OSError, OverflowError, TypeError, RecursionError):
        print(json.dumps({"status": "error", "message": "Invalid or unsupported bounded numerical request."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
