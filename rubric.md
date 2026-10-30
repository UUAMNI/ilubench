# IlùBench Scoring Rubric (v0.3)

Score each A/B response pair (Prompt A = English instruction, Prompt B = Igbo instruction) on the dimensions below. Judges for dimension 4 must be native or near-native Igbo speakers.

## Per-response dimensions

**1. Output language** — `en` / `ig` / `mixed` / `other_lang`.
`other_lang` (added in v0.2) marks a response substantially in a different language altogether, with the identified language recorded alongside (e.g. `other_lang:yo`). The observed failure mode motivating it: an Igbo prompt answered substantially in Yoruba, which v0.1 could only record as `mixed` — losing the finding.

**2. Epistemic frame** — which register does the response occupy?
- `outsider`: explains to a non-member audience; gloss → literal translation → exposition structure; translation is the spine of the response.
- `inside`: assumes cultural familiarity; exposition proceeds from within the tradition; translation absent or vestigial.
- `mixed`: elements of both.

**3. Comparison-anchor source** — when the response reaches for analogies:
- `same_culture`: anchors to other Igbo proverbs or Igbo cultural referents.
- `other_culture:<label>` (changed in v0.3): anchors to proverbs or referents from another culture, and `<label>` names that culture. The label is a lowercase ASCII slug (`[a-z][a-z0-9_]*`), for example `other_culture:english`, `other_culture:yoruba`, `other_culture:pan_african` or `other_culture:generic_western`. When a response anchors to more than one other culture, record the one it leans on most and name the others in the notes.
- `none`: no comparative anchors.

Bare `other_culture`, as recorded under v0.2, stays a valid value. It means the response anchored to another culture that the score did not name.

**4. Cultural correctness** (native-speaker judged, 3-point scale):
- `2`: correct — the reading a culturally fluent speaker would give, including figurative sense.
- `1`: partially correct — right direction, missing or distorting the figurative/applied sense.
- `0`: incorrect — fluent-but-wrong gloss, literalism, or hallucinated referents.

## Pair-level metric

**Register delta** = the change between A and B on dimensions 2–3, reported with the correctness scores:
- `switch_full`: A = outsider AND B = inside (anchor source moves to `same_culture`).
- `switch_partial`: movement on one of frame/anchors but not both.
- `no_switch`: same register in both.
- Report alongside: Δ correctness (does the accessible register change what the user actually gets right?).

The register delta compares anchor source by its base category, the text before `:`. So `other_culture:english` and `other_culture:yoruba` count as the same category, and the register delta means what it meant in v0.2.

## Within-language consistency (added in v0.3)

Within-language consistency asks whether a model gives the same kind of answer when it is asked again in the same language. It is computed per model, per probe, per arm (A = English prompt, B = Igbo prompt) and per dimension.

- Take the set S of samples that have a scored value for that dimension. Values marked `pending_*` and missing values are left out. With n = |S| of 2 or more, consistency = (number of samples with the most common value) / n. With n below 2 it is null and is not reported. Values are compared whole, so for anchor source the label counts (`other_culture:english` and `other_culture:yoruba` are different values here).
- There are two kinds, reported separately and never pooled:
  - `resample`: the canonical wording (`prompt_variant` = `canonical`) asked again in one run, one value per `sample_index`.
  - `paraphrase`: one value per wording, the canonical wording plus each approved native-authored paraphrase, using sample 0 of each.
- Dimensions: output language, epistemic frame and anchor source now. Cultural correctness and `reading` join once native or near-native judges have scored the samples, using the same formula on their values.
- It is reported per arm as **consistency in English** (arm A) and **consistency in Igbo** (arm B), in their own columns beside the register delta. It is never folded into the register delta, never combined into one score with any cross-language figure, never rewarded, and never used to sort or rank models.
- Rows without `sample_group` (every row published before v0.3) are single canonical samples. Two rows for the same model and probe from different dates are never treated as a resample set, because a provider can change a model's weights under the same id.

Rows produced by a run with repeated samples or paraphrases carry four extra fields: `prompt_variant` (`canonical`, or the paraphrase's variant id), `sample_index` (0 to k-1), `samples` (k) and `sample_group` (`<YYYY-MM-DD>_<provider>_<probe_id>_<prompt_variant>`, with the run date in UTC).

## Elicitation constraints

Fresh session per prompt; default model settings; no system prompt or customization; both prompts to the same model version; record model + version + date. Do not paraphrase the probes: the runs files hold only the `probe_set_v0.jsonl` wording. Paraphrased wordings live only in the native-authored paraphrase file (`probe_paraphrases_v0.3.jsonl`), where native or near-native Igbo speakers write and approve them, and they are used only for the within-language consistency measure. Rows elicited with them are written to separate files and never enter the runs files. Repeated samples follow the same constraints, each one a fresh session.

## Versions

- **v0.3** (October 2026). Changes from v0.2: adds within-language consistency (resample and
  paraphrase kinds, reported per arm as consistency in English and consistency in Igbo, kept
  apart from the register delta and from cross-language figures, never rewarded or ranked).
  Dimension 3 names the other culture (`other_culture:<label>`) where v0.2 said
  "English/Western"; bare `other_culture` stays valid, and the register delta compares the
  base category. "Do not paraphrase the probes" now covers the canonical matrix, and
  paraphrased wordings live only in the native-authored paraphrase file. Dimensions 1, 2 and
  4 are unchanged; v0.2 scores remain valid v0.3 scores. v0.2 stays citable as published.
- **v0.2** (August 2026): dimension 1 gains `other_lang` with an
  identified-language subfield (`other_lang:yo` etc.). All other dimensions,
  the pair-level register delta, and the elicitation constraints are
  unchanged; v0.1 scores remain valid v0.2 scores. v0.1 stays citable as
  published.
- **v0.1** (July 2026): initial rubric.

*CC-BY-4.0 · UUAMNI · July to October 2026*
