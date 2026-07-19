# IlùBench Scoring Rubric (v0.1)

Score each A/B response pair (Prompt A = English instruction, Prompt B = Igbo instruction) on the dimensions below. Judges for dimension 4 must be native or near-native Igbo speakers.

## Per-response dimensions

**1. Output language** — `en` / `ig` / `mixed`.

**2. Epistemic frame** — which register does the response occupy?
- `outsider`: explains to a non-member audience; gloss → literal translation → exposition structure; translation is the spine of the response.
- `inside`: assumes cultural familiarity; exposition proceeds from within the tradition; translation absent or vestigial.
- `mixed`: elements of both.

**3. Comparison-anchor source** — when the response reaches for analogies:
- `same_culture`: anchors to other Igbo proverbs or Igbo cultural referents.
- `other_culture`: anchors to English/Western proverbs or referents.
- `none`: no comparative anchors.

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

## Elicitation constraints

Fresh session per prompt; default model settings; no system prompt or customization; both prompts to the same model version; record model + version + date. Do not paraphrase the probes.

*CC-BY-4.0 · UUAMNI · July 2026*
