"""Evaluate the decision pipeline on the labeled dataset.

    python -m evaluation.evaluate                  # uses JEV_BACKEND from .env
    python -m evaluation.evaluate --backend mock   # offline pipeline check (NOT a Jev result)

What it measures
  * classification quality: accuracy, per-class precision/recall/F1, confusion matrix
  * the AUTOMATION trade-off: how many tickets were auto-routed (coverage), and how
    accurate those auto-routed ones were - the number that matters in production
  * calibration of department probabilities: ECE and Brier score
  * operations: inference error rate and latency percentiles
  * a threshold sweep, so you can pick AUTO_ROUTE_MIN_CONFIDENCE from data

Every report records which backend and model produced it. Numbers from the mock backend
measure our plumbing only and must never be quoted as Jev performance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.models.decision import Action, Department, Priority
from app.policies.automation_policy import AutomationPolicy
from app.services.decision_parser import parse_ticket_decision
from app.services.jev_client import JevError, build_jev_client
from app.utils.privacy import redact_pii
from evaluation.metrics import (
    accuracy,
    confusion_matrix,
    expected_calibration_error,
    multiclass_brier,
    per_class_report,
    percentile,
)

DATASET = Path(__file__).parent / "sample_tickets.json"
RESULTS_DIR = Path(__file__).parent / "results"
DEPARTMENTS = [d.value for d in Department]


async def predict_all(settings: Settings, tickets: list[dict], concurrency: int) -> list[dict]:
    """Call Jev once per ticket (bounded concurrency to respect rate limits)."""
    jev = build_jev_client(settings)
    gate = asyncio.Semaphore(concurrency)

    async def one(ticket: dict) -> dict:
        async with gate:
            try:
                result = await jev.evaluate_ticket(redact_pii(ticket["message"]))
                return {
                    "decision": parse_ticket_decision(result.response),
                    "latency_ms": result.latency_ms,
                    "error": None,
                }
            except JevError as exc:
                return {"decision": None, "latency_ms": None, "error": exc.reason}

    try:
        return await asyncio.gather(*(one(t) for t in tickets))
    finally:
        await jev.aclose()


def build_report(tickets: list[dict], preds: list[dict], policy: AutomationPolicy) -> dict:
    y_dept = [t["department"] for t in tickets]
    p_dept = [p["decision"].department.department.value if p["decision"] else None for p in preds]
    y_prio = [t["priority"] for t in tickets]
    p_prio = [p["decision"].priority.priority.value if p["decision"] else None for p in preds]

    actions = [
        policy.evaluate(p["decision"])[0] if p["decision"] else Action.HUMAN_REVIEW for p in preds
    ]
    auto = [i for i, a in enumerate(actions) if a is Action.AUTO_ROUTE]

    ok = [i for i, p in enumerate(preds) if p["decision"]]
    top_prob = [max(preds[i]["decision"].department.probabilities.values()) for i in ok]
    correct = [p_dept[i] == y_dept[i] for i in ok]
    ece, bins = expected_calibration_error(top_prob, correct)
    dists = [
        {k.value: v for k, v in preds[i]["decision"].department.probabilities.items()} for i in ok
    ]

    y_human = [t["needs_human"] for t in tickets]
    p_human = [
        p["decision"].human_review.probability >= policy.human_review_noul_threshold
        if p["decision"]
        else None
        for p in preds
    ]
    human_idx = ok
    latencies = [p["latency_ms"] for p in preds if p["latency_ms"] is not None]

    by_tag: dict[str, list[int]] = {}
    for i, t in enumerate(tickets):
        by_tag.setdefault(t["tag"], []).append(i)

    return {
        "n_tickets": len(tickets),
        "department": {
            "accuracy": accuracy(y_dept, p_dept),
            "per_class": per_class_report(y_dept, p_dept, DEPARTMENTS),
            "confusion_matrix": confusion_matrix(y_dept, p_dept, DEPARTMENTS),
            "accuracy_by_tag": {
                tag: accuracy([y_dept[i] for i in idx], [p_dept[i] for i in idx])
                for tag, idx in sorted(by_tag.items())
            },
        },
        "priority": {
            "accuracy": accuracy(y_prio, p_prio),
            "within_one_level": sum(
                p is not None
                and abs(list(Priority).index(Priority(p)) - list(Priority).index(Priority(t))) <= 1
                for t, p in zip(y_prio, p_prio, strict=True)
            )
            / len(tickets),
        },
        "needs_human_accuracy": accuracy(
            [y_human[i] for i in human_idx], [p_human[i] for i in human_idx]
        )
        if ok
        else None,
        "automation": {
            "coverage": len(auto) / len(tickets),
            "review_rate": 1 - len(auto) / len(tickets),
            "accuracy_on_auto_routed": accuracy(
                [y_dept[i] for i in auto], [p_dept[i] for i in auto]
            )
            if auto
            else None,
            "wrong_auto_routes": sum(p_dept[i] != y_dept[i] for i in auto),
        },
        "calibration": {
            "ece_top_probability": ece,
            "bins": bins,
            "brier": multiclass_brier(dists, [y_dept[i] for i in ok], DEPARTMENTS),
        },
        "operations": {
            "inference_error_rate": 1 - len(ok) / len(tickets),
            "errors": sorted({p["error"] for p in preds if p["error"]}),
            "latency_ms_p50": _round(percentile(latencies, 50)),
            "latency_ms_p95": _round(percentile(latencies, 95)),
        },
    }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def threshold_sweep(tickets, preds, policy: AutomationPolicy) -> list[dict]:
    """Re-apply the policy at different confidence thresholds WITHOUT calling the API again."""
    rows = []
    for threshold in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        trial = replace(policy, auto_route_min_confidence=threshold)
        auto = [
            i
            for i, p in enumerate(preds)
            if p["decision"] and trial.evaluate(p["decision"])[0] is Action.AUTO_ROUTE
        ]
        right = sum(
            preds[i]["decision"].department.department.value == tickets[i]["department"]
            for i in auto
        )
        rows.append(
            {
                "threshold": threshold,
                "coverage": len(auto) / len(tickets),
                "auto_routed": len(auto),
                "accuracy_on_auto_routed": right / len(auto) if auto else None,
            }
        )
    return rows


def print_report(meta: dict, report: dict, sweep: list[dict]) -> None:
    if meta["backend"] == "mock":
        print("=" * 72)
        print(" OFFLINE MOCK BACKEND - these numbers test the PIPELINE, not Jev.")
        print(" Do not quote them as model performance.")
        print("=" * 72)
    print(f"backend={meta['backend']} models={meta['models']} n={report['n_tickets']}")
    d, a, c, o = (
        report["department"],
        report["automation"],
        report["calibration"],
        report["operations"],
    )
    print(
        f"\nDepartment accuracy      {d['accuracy']:.3f}   "
        f"macro-F1 {d['per_class']['macro_avg']['f1']:.3f}"
    )
    for label in DEPARTMENTS:
        r = d["per_class"][label]
        print(
            f"  {label:<10} P={r['precision']:.2f} R={r['recall']:.2f} "
            f"F1={r['f1']:.2f} n={r['support']}"
        )
    print(
        "  accuracy by tag: " + ", ".join(f"{k}={v:.2f}" for k, v in d["accuracy_by_tag"].items())
    )
    print("\nConfusion matrix (rows=true, cols=predicted)")
    cols = [*DEPARTMENTS, "none"]
    print("            " + " ".join(f"{col[:6]:>6}" for col in cols))
    for true_label, row in d["confusion_matrix"].items():
        print(f"  {true_label:<10}" + " ".join(f"{row[col]:>6}" for col in cols))
    print(
        f"\nPriority accuracy        {report['priority']['accuracy']:.3f}   "
        f"within one level {report['priority']['within_one_level']:.3f}"
    )
    print(f"Needs-human accuracy     {report['needs_human_accuracy']}")
    acc_auto = a["accuracy_on_auto_routed"]
    print(f"\nAutomation coverage      {a['coverage']:.3f}   review rate {a['review_rate']:.3f}")
    print(
        f"Accuracy on auto-routed  {acc_auto if acc_auto is None else f'{acc_auto:.3f}'}"
        f"   wrong auto-routes {a['wrong_auto_routes']}"
    )
    print(
        f"\nCalibration  ECE={c['ece_top_probability']:.3f}  Brier={c['brier']:.3f}"
        "  (small n: treat as indicative only)"
    )
    print(
        f"Errors {o['inference_error_rate']:.3f} {o['errors']}  "
        f"latency p50={o['latency_ms_p50']} p95={o['latency_ms_p95']} ms"
    )
    print("\nThreshold sweep (AUTO_ROUTE_MIN_CONFIDENCE; other rules unchanged)")
    for row in sweep:
        acc = row["accuracy_on_auto_routed"]
        print(
            f"  {row['threshold']:.1f}  coverage={row['coverage']:.2f}  "
            f"auto={row['auto_routed']:>2}  accuracy_on_auto={'-' if acc is None else f'{acc:.2f}'}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--backend", choices=["typesafe", "mock"], help="override JEV_BACKEND")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()

    settings = Settings()
    if args.backend:
        settings = settings.model_copy(update={"jev_backend": args.backend})
    tickets = json.loads(args.dataset.read_text())["tickets"]
    policy = AutomationPolicy.from_settings(settings)

    preds = asyncio.run(predict_all(settings, tickets, args.concurrency))
    report = build_report(tickets, preds, policy)
    sweep = threshold_sweep(tickets, preds, policy)
    meta = {
        "backend": settings.jev_backend,
        "models": sorted({p["decision"].model for p in preds if p["decision"]}),
        "dataset": args.dataset.name,
        "policy": {
            k: (sorted(v) if isinstance(v, frozenset) else v) for k, v in vars(policy).items()
        },
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    print_report(meta, report, sweep)

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"report_{meta['backend']}_{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    out.write_text(
        json.dumps(
            {"meta": meta, "report": report, "threshold_sweep": sweep}, indent=2, default=str
        )
    )
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
