"""Item-level summary of an evaluation, and its paired difference to a second one.

Uses the report's convention: for each of the 60 items (scene x input position) average the
metric over the 8 frames that are not the input, then report the mean and the standard
error over items. The paired block compares the two runs item by item (same scenes and
input positions), as in the report's paired table.

usage: python scripts/retrain_summary.py <metrics.json> [<reference metrics.json>]
"""
import json
import math
import sys

METRICS = ("psnr", "ssim", "lpips")


def per_item(path: str) -> dict[tuple[str, int], dict[str, float]]:
    with open(path) as f:
        items = json.load(f)["items"]
    out = {}
    for it in items:
        frames = [fr for fr in it["frames"] if fr["i"] != it["in_pos"]]
        row = {m: sum(fr[m] for fr in frames) / len(frames) for m in METRICS}
        out[(it["scene"], it["in_pos"])] = {**row, "rho": it["rho"]}
    return out


def mean_se(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        sys.exit("need at least 2 items to compute a standard error (found %d)" % n)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var / n)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = per_item(sys.argv[1])
    summary = {}
    for m in (*METRICS, "rho"):
        mean, se = mean_se([row[m] for row in run.values()])
        summary[m] = {"mean": mean, "se": se}
    result = {"n_items": len(run), "summary": summary}
    if len(sys.argv) > 2:
        ref = per_item(sys.argv[2])
        shared = sorted(set(run) & set(ref))
        paired = {}
        for m in (*METRICS, "rho"):
            diffs = [run[k][m] - ref[k][m] for k in shared]
            mean, se = mean_se(diffs)
            paired[m] = {"mean_diff": mean, "se": se, "t": mean / se if se else float("nan"),
                         "first_higher": sum(d > 0 for d in diffs), "n": len(diffs)}
        result["paired_vs_reference"] = paired
    json.dump(result, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
