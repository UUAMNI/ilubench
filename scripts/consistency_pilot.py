#!/usr/bin/env python3
"""IlùBench accidental test-retest pilot (confounded).

Reads the published runs files and finds rows where the same model id answered
the same probe through the same provider and interface on two different dates.
For each such pair it counts, per arm and per dimension, whether the stored
value is the same on both dates.

These counts are a pilot and stay apart from rubric v0.3 within-language
consistency. Rubric v0.3 counts only samples taken within one run. Between two
dates a provider can change a model's weights or defaults under the same id, so
a match or a mismatch here mixes any change in the model with ordinary sampling
variation. Rows still marked pending_* on either date are left out of the
counts and reported as not comparable.

Only single canonical samples are read: rows without sampling fields, or
sample 0 of the canonical wording. Paraphrase rows are never read.

Usage:
    python3 scripts/consistency_pilot.py
    python3 scripts/consistency_pilot.py --json
    python3 scripts/consistency_pilot.py runs_v0.jsonl runs_v0.1.5.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [REPO / "runs_v0.jsonl", REPO / "runs_v0.1.5.jsonl"]
DIMENSIONS = ("output_language", "epistemic_frame", "anchor_source")
ARMS = (("arm_A", "A (English prompt)"), ("arm_B", "B (Igbo prompt)"))

CAVEAT = (
    "Confounded pilot. Same model id, provider, interface and probe on two dates. "
    "A provider can change a model's weights or defaults under the same id between "
    "dates, so these counts mix any change in the model with sampling variation. "
    "Rubric v0.3 within-language consistency uses only samples from one run; these "
    "counts are kept apart from it and are never used to rank models. output_language "
    "is the value stored in the file (the runner's en / ig / mixed heuristic); the live "
    "leaderboard rescores it under rubric v0.2, and a row's notes can qualify it."
)


def scored(value) -> bool:
    """A value that can be compared: present, non-empty, not pending_*."""
    return isinstance(value, str) and value.strip() != "" and not value.startswith("pending_")


def load_rows(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("prompt_variant", "canonical") != "canonical":
                    continue
                if row.get("sample_index", 0) != 0:
                    continue
                row["_source"] = f"{path.name}:{lineno}"
                rows.append(row)
    return rows


def find_pairs(rows: list[dict]) -> list[tuple[dict, dict]]:
    """Every pair of rows with the same model, provider, interface and probe
    and different dates, earlier row first."""
    by_key: dict = defaultdict(list)
    for row in rows:
        key = (row.get("model"), row.get("provider", ""), row.get("interface"), row.get("probe_id"))
        by_key[key].append(row)
    pairs = []
    for group in by_key.values():
        group.sort(key=lambda r: r.get("date", ""))
        for i, first in enumerate(group):
            for second in group[i + 1:]:
                if first.get("date") != second.get("date"):
                    pairs.append((first, second))
    return pairs


def tally(pairs: list[tuple[dict, dict]]) -> list[dict]:
    """One entry per model, provider, interface and date pair."""
    groups: dict = {}
    for first, second in pairs:
        key = (first.get("model"), first.get("provider", ""), first.get("interface"),
               first.get("date"), second.get("date"))
        if key not in groups:
            groups[key] = {
                "model": key[0], "provider": key[1], "interface": key[2],
                "dates": [key[3], key[4]], "probes": [], "sources": [],
                "arms": {arm: {dim: {"matched": 0, "compared": 0, "not_comparable": 0,
                                     "differences": []}
                               for dim in DIMENSIONS}
                         for arm, _ in ARMS},
            }
        entry = groups[key]
        pid = first.get("probe_id")
        entry["probes"].append(pid)
        entry["sources"].append([first["_source"], second["_source"]])
        for arm, _ in ARMS:
            a, b = first.get(arm) or {}, second.get(arm) or {}
            for dim in DIMENSIONS:
                cell = entry["arms"][arm][dim]
                va, vb = a.get(dim), b.get(dim)
                if not (scored(va) and scored(vb)):
                    cell["not_comparable"] += 1
                    continue
                cell["compared"] += 1
                if va == vb:
                    cell["matched"] += 1
                else:
                    cell["differences"].append({"probe_id": pid, "first": va, "second": vb})
    return sorted(groups.values(), key=lambda g: (str(g["model"]), g["dates"]))


def render(entries: list[dict], paths: list[Path]) -> str:
    lines = ["IlùBench accidental test-retest pilot (confounded)", "", CAVEAT, "",
             "Files read: " + ", ".join(p.name for p in paths), ""]
    if not entries:
        lines.append("No overlapping rows found.")
        return "\n".join(lines) + "\n"
    for e in entries:
        lines.append(f"{e['model']} ({e['provider'] or 'no provider'}, {e['interface']}): "
                     f"{e['dates'][0]} and {e['dates'][1]}, probes {', '.join(e['probes'])}")
        for arm, label in ARMS:
            lines.append(f"  arm {label}")
            for dim in DIMENSIONS:
                c = e["arms"][arm][dim]
                if c["compared"]:
                    text = f"same value on {c['matched']} of {c['compared']} probes"
                    for d in c["differences"]:
                        text += (f"; {d['probe_id']}: {d['first']} on {e['dates'][0]}, "
                                 f"{d['second']} on {e['dates'][1]}")
                else:
                    text = "no comparable values"
                if c["not_comparable"]:
                    text += f" ({c['not_comparable']} not comparable: pending or missing on a date)"
                lines.append(f"    {dim}: {text}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="IlùBench accidental test-retest pilot (confounded)")
    ap.add_argument("files", nargs="*", type=Path, help="runs JSONL files (default: the published two)")
    ap.add_argument("--json", action="store_true", help="print the counts as JSON")
    args = ap.parse_args(argv)
    paths = args.files or DEFAULT_FILES
    entries = tally(find_pairs(load_rows(paths)))
    if args.json:
        print(json.dumps({"caveat": CAVEAT, "files": [p.name for p in paths], "pairs": entries},
                         ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(render(entries, paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
