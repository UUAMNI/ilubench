#!/usr/bin/env python3
"""IlùBench API evidence runs (v0.1.1, task 2 of the 2026-07-18 weekend directive).

Sends BOTH arms of each probe (prompt_en = arm A, prompt_ig = arm B) to each
provider's API. One fresh call per arm, no system prompt, provider defaults
(no temperature/top_p overrides). Records:

- FULL raw responses + exact model IDs + date -> runs_api_raw/  (git-ignored,
  never uploaded to HF; local evidence archive)
- structured rows appended to runs_v0.jsonl with "interface": "API".

Scoring stays human: output_language is filled by a conservative script
heuristic and notes are filled with factual descriptions (length, opening
line, raw-file pointer). epistemic_frame, anchor_source, register_delta, and
reading are stamped "pending_human_score"; cultural_correctness stays
"pending_native_review". The script never scores a rubric axis.

Keys: read field-by-field from ~/Postman/Github/api_keys.json (fallback:
ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / MOONSHOT_API_KEY env
vars). Keys are never printed and never written into any output file.

Usage:
    python3 scripts/run_probes.py --dry-run
    python3 scripts/run_probes.py                       # ilu-002..005, 3 providers
    python3 scripts/run_probes.py --providers anthropic,openai,google,moonshot
    python3 scripts/run_probes.py --probes ilu-002,ilu-003
    python3 scripts/run_probes.py --samples 5           # within-language consistency
    python3 scripts/run_probes.py --paraphrases probe_paraphrases_v0.3.jsonl

Repeated samples and paraphrased wordings (rubric v0.3, within-language
consistency). --samples K asks each wording K times, each a fresh call.
--paraphrases PATH adds the approved, native-authored wordings in that file;
a row that is not approved or has an empty prompt is skipped with a line on
stderr. With either flag, every row gains prompt_variant, sample_index,
samples and sample_group, run ids gain -<prompt_variant>-s<index>, raw
archive names gain _s<index>, and paraphrase
rows are appended to runs_v0_paraphrases.jsonl so they stay out of
runs_v0.jsonl. With neither flag the output is byte-identical to v0.1.1.
The same contract is implemented by ilubench-runner (Go) and read by Uche's
IlùBench scorer; keep field names, file names and skip lines in step.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBE_SET = REPO / "probe_set_v0.jsonl"
RUNS = REPO / "runs_v0.jsonl"
# Paraphrase rows never enter the canonical matrix files (rubric v0.3).
PARAPHRASE_RUNS = REPO / "runs_v0_paraphrases.jsonl"
RAW_DIR = REPO / "runs_api_raw"
KEYS_FILE = Path.home() / "Postman" / "Github" / "api_keys.json"

DEFAULT_PROBES = ["ilu-002", "ilu-003", "ilu-004", "ilu-005"]
DEFAULT_PROVIDERS = ["anthropic", "openai", "google"]  # moonshot opt-in via --providers

MODEL_IDS = {
    "anthropic": "claude-fable-5",
    "openai": "gpt-5.6",
    "google": "gemini-3.1-pro-preview",  # API name for the UI's Gemini 3.1 Pro (bare -pro 404s)
    "moonshot": None,  # resolved at runtime from /v1/models (kimi 3 naming unverified)
}

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
}

MAX_TOKENS = 2048
TIMEOUT_S = 120

# The probe_set_v0.jsonl wording; paraphrase variant ids may not use it.
CANONICAL = "canonical"
VARIANT_ID = re.compile(r"[a-z][a-z0-9_]*")
PARAPHRASE_REQUIRED = ("probe_id", "variant", "prompt_en", "prompt_ig", "status")


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


def load_key(provider: str) -> str | None:
    """One provider's key, from api_keys.json field or env var. Never printed."""
    if KEYS_FILE.exists():
        try:
            value = json.load(open(KEYS_FILE)).get(provider)
            if value and "PASTE" not in value:
                return value
        except Exception:
            pass
    return os.environ.get(ENV_KEYS[provider]) or None


# ---------------------------------------------------------------------------
# Provider calls (plain HTTPS, no SDK dependencies)
# ---------------------------------------------------------------------------


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    """POST with retry: providers intermittently return 401/429/5xx under
    bursty sequential calls (observed: OpenAI 401s between successful calls
    in the same run). Retries are safe — calls are idempotent reads."""
    body = json.dumps(payload).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(4):
        if attempt:
            time.sleep(8 * attempt)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in (401, 408, 429, 500, 502, 503, 529):
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
    raise last_err


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)


def call_anthropic(key: str, model: str, prompt: str) -> tuple[str, str, dict]:
    raw = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        },
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    text = "".join(b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text")
    return text, raw.get("model", model), raw


def call_openai_compatible(base: str, key: str, model: str, prompt: str) -> tuple[str, str, dict]:
    raw = _post_json(
        f"{base}/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}]},
        {"Authorization": f"Bearer {key}"},
    )
    text = raw["choices"][0]["message"]["content"] or ""
    return text, raw.get("model", model), raw


def call_google(key: str, model: str, prompt: str) -> tuple[str, str, dict]:
    raw = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"contents": [{"parts": [{"text": prompt}]}]},
        {"x-goog-api-key": key},
    )
    parts = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return text, raw.get("modelVersion", model), raw


def resolve_moonshot_model(key: str) -> str:
    """Pick the Kimi 3 model id from Moonshot's model list (naming unverified
    at authoring time). Prefers ids containing 'k3' or 'kimi-3'; falls back to
    the newest kimi id and says so."""
    listing = _get_json(
        "https://api.moonshot.ai/v1/models", {"Authorization": f"Bearer {key}"}
    )
    ids = [m.get("id", "") for m in listing.get("data", [])]
    for pattern in (r"k3", r"kimi-?3"):
        hits = [i for i in ids if re.search(pattern, i, re.I)]
        if hits:
            return sorted(hits)[-1]
    kimi = sorted(i for i in ids if "kimi" in i.lower())
    if not kimi:
        raise RuntimeError(f"no kimi model found in Moonshot listing ({len(ids)} ids)")
    print(f"  WARNING: no Kimi-3-looking id; using newest kimi id {kimi[-1]!r}")
    return kimi[-1]


def call_provider(provider: str, key: str, model: str, prompt: str) -> tuple[str, str, dict]:
    if provider == "anthropic":
        return call_anthropic(key, model, prompt)
    if provider == "openai":
        return call_openai_compatible("https://api.openai.com/v1", key, model, prompt)
    if provider == "moonshot":
        return call_openai_compatible("https://api.moonshot.ai/v1", key, model, prompt)
    if provider == "google":
        return call_google(key, model, prompt)
    raise ValueError(provider)


# ---------------------------------------------------------------------------
# Output-language heuristic (conservative; everything else is human-scored)
# ---------------------------------------------------------------------------

_IGBO_MARKERS = re.compile(r"[ịọụṅỊỌỤṄ]")
_IGBO_WORDS = {
    "na", "bụ", "nke", "ya", "a", "ilu", "ihe", "ndị", "n'ala", "mmadụ",
    "igbo", "anyị", "gị", "ha", "dị", "ka", "ma", "ga-", "kwuru", "pụtara",
}


def detect_output_language(text: str) -> str:
    """'ig' / 'en' / 'mixed' via diacritic + stopword density. Conservative:
    anything genuinely bilingual lands on 'mixed'."""
    if not text.strip():
        return "empty"
    words = re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", unicodedata.normalize("NFC", text.lower()))
    if not words:
        return "empty"
    igbo_hits = sum(1 for w in words if _IGBO_MARKERS.search(w) or w in _IGBO_WORDS)
    ratio = igbo_hits / len(words)
    if ratio >= 0.35:
        return "ig"
    if ratio <= 0.05:
        return "en"
    return "mixed"


def factual_notes(text: str, raw_path: Path) -> str:
    """Short factual description. No rubric judgment."""
    words = len(text.split())
    opening = " ".join(text.strip().split())[:90]
    return (
        f"API run, auto-captured. ~{words} words. Opens: \"{opening}...\". "
        f"Full raw response: {raw_path.relative_to(REPO)}. "
        "Rubric axes pending human score."
    )


# ---------------------------------------------------------------------------
# Repeated samples and paraphrased wordings (rubric v0.3)
# ---------------------------------------------------------------------------


def positive_int(text: str) -> int:
    """argparse type for --samples: ASCII digits only, at least 1."""
    if not re.fullmatch(r"[0-9]+", text) or int(text) < 1:
        raise argparse.ArgumentTypeError(
            f"expected a whole number of 1 or more, got {text!r}"
        )
    return int(text)


class ParaphraseFileError(ValueError):
    """The paraphrase file cannot be read as rows (bad JSON, missing field)."""


def paraphrase_skip_reason(row: dict, seen: set) -> str | None:
    """Why a well-formed paraphrase row cannot run, or None if it can."""
    variant = row["variant"]
    if variant == CANONICAL:
        return "variant id canonical is reserved for the probe set wording"
    if not VARIANT_ID.fullmatch(variant):
        return "variant id must be lowercase letters, digits or underscores, starting with a letter"
    if (row["probe_id"], variant) in seen:
        return "repeats an earlier row for this probe and variant"
    if row["status"] != "approved":
        return f"status is {row['status']} (only approved rows run)"
    empty = [k for k in ("prompt_en", "prompt_ig") if not row[k].strip()]
    if empty:
        return " and ".join(empty) + " empty"
    return None


def load_paraphrases(path: str, probe_ids: list[str], warn) -> tuple[dict, int]:
    """Approved paraphrase wordings for the probes in this run.

    Returns ({probe_id: [(variant, prompt_en, prompt_ig), ...]}, skipped), in
    file order. Rows for probes outside this run are ignored. A row that
    cannot run (not approved, an empty prompt, a reserved or malformed variant
    id, a repeat) is skipped and reported through warn(). Raises
    FileNotFoundError, OSError or ParaphraseFileError.
    """
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise ParaphraseFileError("not valid UTF-8") from None
    wordings: dict = {pid: [] for pid in probe_ids}
    seen: set = set()
    skipped = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            raise ParaphraseFileError(f"line {lineno}: invalid JSON") from None
        if not isinstance(row, dict):
            raise ParaphraseFileError(f"line {lineno}: not a JSON object")
        for key in PARAPHRASE_REQUIRED:
            if key not in row:
                raise ParaphraseFileError(f"line {lineno}: missing '{key}'")
            if not isinstance(row[key], str):
                raise ParaphraseFileError(f"line {lineno}: '{key}' must be a string")
        pid, variant = row["probe_id"], row["variant"]
        if pid not in wordings:
            continue
        reason = paraphrase_skip_reason(row, seen)
        seen.add((pid, variant))
        if reason:
            warn(f"skipped paraphrase {pid} {variant}: {reason}")
            skipped += 1
            continue
        wordings[pid].append((variant, row["prompt_en"], row["prompt_ig"]))
    return wordings, skipped


def sample_names(today: str, prov: str, pid: str, variant: str, index: int) -> tuple[str, str, str]:
    """(run_id, raw-file prefix, evidence glob) for one sample of one wording.

    The run_id ends in -<prompt_variant>-s<index>, the key Uche's importer
    stores a sampled row under, so every sample's row is distinct. Archive
    names end in _s<index>; paraphrase archives also carry the variant id so
    they never overwrite the canonical ones.
    """
    prefix = f"{today}_{prov}_{pid}" + ("" if variant == CANONICAL else f"_{variant}")
    run_id = f"run-{today}-api-{prov}-{pid}-{variant}-s{index}"
    evidence = f"runs_api_raw/{prefix}_arm_*_s{index}.json (local archive, not uploaded)"
    return run_id, prefix, evidence


def append_rows(path: Path, rows: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="IlùBench API evidence runs")
    ap.add_argument("--probes", default=",".join(DEFAULT_PROBES))
    ap.add_argument("--providers", default=",".join(DEFAULT_PROVIDERS))
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no API calls, no writes.")
    ap.add_argument("--samples", type=positive_int, default=1, metavar="K",
                    help="Ask each wording K times, each a fresh call (default 1).")
    ap.add_argument("--paraphrases", default=None, metavar="PATH",
                    help="Also run the approved wordings in this paraphrase file "
                         "(e.g. probe_paraphrases_v0.3.jsonl). Their rows go to "
                         f"{PARAPHRASE_RUNS.name}.")
    args = ap.parse_args()

    probe_ids = [p.strip() for p in args.probes.split(",") if p.strip()]
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    for p in providers:
        if p not in ENV_KEYS:
            print(f"ERROR: unknown provider {p!r}")
            return 1

    probes = {}
    for line in open(PROBE_SET, encoding="utf-8"):
        d = json.loads(line)
        probes[d["id"]] = d
    missing = [p for p in probe_ids if p not in probes]
    if missing:
        print(f"ERROR: probes not in {PROBE_SET.name}: {missing}")
        return 1

    # Sampled mode adds the four v0.3 fields; without it, output is unchanged.
    sampled = args.samples > 1 or bool(args.paraphrases)
    paraphrases: dict = {}
    if args.paraphrases:
        try:
            paraphrases, skipped = load_paraphrases(
                args.paraphrases, probe_ids, lambda msg: print(msg, file=sys.stderr)
            )
        except FileNotFoundError:
            print(f"ERROR: paraphrase file not found: {args.paraphrases}")
            return 1
        except ParaphraseFileError as e:
            print(f"ERROR: bad paraphrase file {args.paraphrases}: {e}")
            return 1
        except OSError:
            print(f"ERROR: could not read paraphrase file: {args.paraphrases}")
            return 1
        approved = sum(len(v) for v in paraphrases.values())
        print(f"paraphrases: {approved} approved wording(s) to run, {skipped} row(s) skipped "
              f"({args.paraphrases})", file=sys.stderr)
    wordings = {
        pid: [(CANONICAL, probes[pid]["prompt_en"], probes[pid]["prompt_ig"])] + paraphrases.get(pid, [])
        for pid in probe_ids
    }

    today = str(date.today())
    plan = [(pid, prov) for pid in probe_ids for prov in providers]
    if sampled:
        calls = sum(len(wordings[pid]) for pid, _ in plan) * args.samples * 2
        print(f"Plan: {len(plan)} probe x provider pairs, {args.samples} sample(s) per wording "
              f"({calls} API calls)")
        for pid, prov in plan:
            names = ", ".join(w[0] for w in wordings[pid])
            print(f"  {pid} x {prov} (model: {MODEL_IDS[prov] or 'resolved at runtime'}; "
                  f"wordings: {names})")
    else:
        print(f"Plan: {len(plan)} probe x provider pairs ({len(plan) * 2} API calls)")
        for pid, prov in plan:
            print(f"  {pid} x {prov} (model: {MODEL_IDS[prov] or 'resolved at runtime'})")

    if args.dry_run:
        key_status = {p: ("OK" if load_key(p) else "MISSING") for p in providers}
        print(f"Key status: {key_status}")
        print("Dry run complete. No calls made, nothing written.")
        return 0

    # Key check upfront so a missing key aborts before any spend.
    keys = {}
    for p in providers:
        k = load_key(p)
        if not k:
            print(f"ERROR: no key for {p!r} (fill {KEYS_FILE} or set {ENV_KEYS[p]}).")
            return 1
        keys[p] = k

    models = dict(MODEL_IDS)
    if "moonshot" in providers:
        models["moonshot"] = resolve_moonshot_model(keys["moonshot"])
        print(f"  moonshot model resolved: {models['moonshot']}")

    RAW_DIR.mkdir(exist_ok=True)
    (RAW_DIR / ".gitignore").write_text("*\n")  # belt: never enters any git repo

    new_rows = []  # canonical wording -> RUNS
    paraphrase_rows = []  # paraphrase wordings -> PARAPHRASE_RUNS
    failures = 0
    # sample_group carries the run date in UTC, fixed once for the whole run.
    run_date_utc = datetime.now(timezone.utc).date().isoformat()
    for pid, prov in plan:
        model = models[prov]
        for variant, prompt_en, prompt_ig in wordings[pid]:
            for index in range(args.samples):
                if sampled:
                    run_id, prefix, evidence = sample_names(today, prov, pid, variant, index)
                    label = f"{pid} x {prov} {variant} s{index}"
                    suffix = f"_s{index}"
                    sample_fields = {
                        "prompt_variant": variant,
                        "sample_index": index,
                        "samples": args.samples,
                        "sample_group": f"{run_date_utc}_{prov}_{pid}_{variant}",
                    }
                else:
                    run_id = f"run-{today}-api-{prov}-{pid}"
                    prefix = f"{today}_{prov}_{pid}"
                    evidence = f"runs_api_raw/{today}_{prov}_{pid}_*.json (local archive, not uploaded)"
                    label = f"{pid} x {prov}"
                    suffix = ""
                    sample_fields = {}
                arms = {}
                reported_model = model
                failed = False
                for arm_name, prompt in (("arm_A", prompt_en), ("arm_B", prompt_ig)):
                    try:
                        text, reported_model, raw = call_provider(prov, keys[prov], model, prompt)
                    except Exception as e:
                        print(f"  FAIL {label} {arm_name}: {type(e).__name__}: {e}")
                        failed = True
                        break
                    raw_path = RAW_DIR / f"{prefix}_{arm_name}{suffix}.json"
                    raw_path.write_text(
                        json.dumps(
                            {
                                "date_utc": datetime.now(timezone.utc).isoformat(),
                                "provider": prov,
                                "requested_model": model,
                                "reported_model": reported_model,
                                "probe_id": pid,
                                "arm": arm_name,
                                **sample_fields,
                                "prompt": prompt,
                                "response_text": text,
                                "raw_api_response": raw,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    arms[arm_name] = {
                        "output_language": detect_output_language(text),
                        "epistemic_frame": "pending_human_score",
                        "anchor_source": "pending_human_score",
                        "notes": factual_notes(text, raw_path),
                    }
                    print(f"  ok {label} {arm_name}: {arms[arm_name]['output_language']}")
                if failed:
                    failures += 1
                    continue

                row = {
                    "run_id": run_id,
                    "date": today,
                    "model": reported_model,
                    "interface": "API",
                    "probe_id": pid,
                    **sample_fields,
                    "arm_A": arms["arm_A"],
                    "arm_B": arms["arm_B"],
                    "register_delta": "pending_human_score",
                    "reading": "pending_human_score",
                    "cultural_correctness": "pending_native_review",
                    "evidence": evidence,
                }
                (new_rows if variant == CANONICAL else paraphrase_rows).append(row)

    if new_rows:
        append_rows(RUNS, new_rows)
    if paraphrase_rows:
        append_rows(PARAPHRASE_RUNS, paraphrase_rows)
    if sampled:
        summary = f"\nAppended {len(new_rows)} rows to {RUNS.name}"
        if args.paraphrases:
            summary += f" and {len(paraphrase_rows)} rows to {PARAPHRASE_RUNS.name}"
        print(f"{summary} ({failures} sample(s) failed).")
        return 0 if failures == 0 else 2
    print(f"\nAppended {len(new_rows)} rows to {RUNS.name} "
          f"({len(plan) - len(new_rows)} pair(s) failed).")
    return 0 if len(new_rows) == len(plan) else 2


if __name__ == "__main__":
    sys.exit(main())
