---
license: cc-by-4.0
language:
  - ig
  - en
task_categories:
  - text-generation
  - question-answering
tags:
  - cultural-reasoning
  - benchmark
  - igbo
  - african-languages
  - evaluation
  - alignment
pretty_name: "IlùBench: Cultural Register Switching in Frontier Language Models"
size_categories:
  - n<1K
configs:
  - config_name: probes
    data_files: probe_set_v0.jsonl
  - config_name: runs
    data_files: runs_v0.jsonl
---

# IlùBench v0.1 — Cultural Register Switching in Frontier Language Models

**The first reproducible protocol for measuring cultural register switching in an African language.** *Ilù* = proverb (Igbo).

**Author:** Chuma B. Chukwu Jr. (UUAMNI)
**Released:** July 2026 · **License:** CC-BY-4.0 · **Contact:** chuma@uuamni.com · [uuamni.com](https://uuamni.com)

**Run it yourself:** [github.com/UUAMNI/ilubench-runner](https://github.com/UUAMNI/ilubench-runner) — a single-file, dependency-free runner that reproduces this protocol against your own API keys (any provider, including local open-weight models) in under five minutes. Contributions of new model runs welcome.

## The finding

Ask a frontier model to explain an Igbo proverb **in English**, and it answers as an outsider: gloss, literal translation, comparisons to English proverbs. Ask the *same model* the *same question* **in Igbo**, and it answers from inside the culture: it reasons from *other Igbo proverbs*, drops the translation scaffolding, and shifts to the hortatory register the form actually carries. The model holds both modes. **Prompt language gates which one the user can reach** — and the English-speaking user cannot access the inside-the-culture register even when asking about the culture. We call this *cultural register switching*.

### Reproduce it in two prompts

> **Prompt A (English):** Explain this proverb: *Gidi gidi bụ ugwu eze.*
> **Prompt B (Igbo):** Kọwaa ilu a: *Gidi gidi bụ ugwu eze.*

We first observed the effect in May 2026 and re-ran the protocol on three current frontier models on July 18, 2026 (Claude Fable 5, Gemini 3.1 Pro, GPT-5.5 — chat interfaces, fresh incognito/temporary sessions, default settings). **Register switching reproduced on all three** (full switch on two; one model now appends a bilingual scaffold to its Igbo response — register behavior shifts across model versions, which is why this benchmark is dated and versioned). Structured records: `runs_v0.jsonl`. The result is not that Prompt B answers in Igbo — it's that **the two responses are not the same explanation translated**:

| Dimension | English-prompted | Igbo-prompted |
|---|---|---|
| Epistemic frame | Outsider explaining to non-Igbo audience: gloss → translation → exposition | Inside-the-culture exposition |
| Literal translation | The response's spine | Absent or vestigial |
| Comparison anchors | English proverbs ("unity is strength") | **Other Igbo proverbs** (*Igwe bụ ike*, *Umunna bụ ike*) |
| Closing register | Descriptive | Hortatory, prescriptive |

## Why it matters

Fluency is not alignment: a model can achieve native-level fluency in a language yet fail to reason as its speakers reason. Existing benchmarks — built largely on single-gold-answer formats from English-native annotation pipelines — are structurally insensitive to this difference: both responses above would score as "correct." Meanwhile, safety alignment measurably degrades in these languages (English refusal rates of ~90% fall to 35–55% for Yoruba, Hausa, and Igbo; LSR Benchmark, arXiv:2603.19273; see also Huang et al., arXiv:2405.10936 on multilingual jailbreaks). Register access and safety transfer are two faces of the same missing layer: **no structured preference data of culturally grounded reasoning exists for Igbo or any African language.** IlùBench measures the gap; the preference dataset we are building (native-annotated, 8 tracks) closes it.

## Protocol (v0)

1. **Probe set:** paired A/B prompts over Igbo proverbs (`probe_set_v0.jsonl` — seed set this release; expanded set in v0.2).
2. **Elicitation:** both prompts to the same model, fresh sessions, default settings, no system customization.
3. **Scoring (per response pair):** see `rubric.md` — output language; epistemic frame; comparison-anchor source; cultural correctness (native-speaker judged, 3-point scale).
4. **Reported metric:** the **register delta** — does the model switch registers between A and B, and does switching change cultural correctness?

**A second observation from the July runs:** the three models do not agree on what the proverb *means*. Two render *gidi gidi* as multitude/crowd (a unity reading); one renders it as strength/majestic bearing (a dignity reading) — fluently and confidently, in both languages. Whether that is a legitimate secondary reading or a fluent-but-wrong gloss is exactly what native-speaker-judged cultural correctness (rubric dimension 4) exists to adjudicate; adjudication is pending and will ship with v1. A benchmark scored only on fluency or structure cannot see this divergence at all.

**Open replication questions:** does the effect hold across other frontier and open models? Across other languages (Yoruba, Hausa, Swahili, Arabic, Mandarin)? If universal, it's a general property of preference-tuned models; if selective, the selectivity is the finding. Replications welcome — open an issue or write us.

## Limitations (v0.1)

Seed probe set of five attested proverbs (expanded set with dialect metadata in v0.2). The July 2026 multi-model evidence (`runs_v0.jsonl`) covers the flagship probe (ilu-001); runs over the remaining seed probes will land as v0.1.x updates. Manual elicitation protocol; scored multi-model runs with native-speaker judges ship as v1. The finding was first observed and documented May 2026 in our internal experiment logs; this release establishes the public protocol.

## Versioning

- **v0.1 (July 2026):** protocol + seed probes + rubric.
- **v0.1.1 (shipped):** related work section + API evidence runs over the remaining seed probes.
- **v0.1.2 (shipped):** related-work precision pass (Multicultural Riddles characterization corrected against the collaborator proposal; community count softened pending verified figure).
- **v0.1.3 (August 2026):** API evidence runs for xAI Grok (grok-4.5) across all five seed probes; rubric scoring pending.
- **v0.1.4 (August 2026):** kimi-k3 run on ilu-001 completes the 5 model x 5 probe matrix (25 rows); the Igbo arm was again substantially Yoruba and is annotated on the row. Rubric scoring pending.
- **v0.2:** expanded probe set (25+), dialect metadata.
- **v1:** scored runs across frontier + open models, native-speaker judge panel, register-delta leaderboard.
- Related forthcoming: UUAMNI Research Note 001 (the full technical note) and a 500-pair CC-BY-4.0 public sample of the Igbo preference dataset.

## Related work

IlùBench sits in a fast-growing family of culturally grounded evaluations, and measures a different axis than its neighbors. Cultural-knowledge benchmarks test what a model knows of a culture, from direct QA to indirect reference resolution: Afri-MCQA (multimodal cultural QA for African languages, arXiv:2601.05699), the Cohere Labs community Multicultural Riddles Benchmark (in progress; original riddles written from scratch by native speakers across dozens of language communities, deliberately indirect so that solving them requires genuine cultural knowledge rather than lookup), BLEnD, and CulturalBench. Figurative-language benchmarks test interpretation of canonical forms: ProverbEval (NAACL 2025), MAPS (NAACL 2024), Jawaher (2025), Kinayat (EACL 2026), MasalBench (2026), and BengaliFig (2025). Safety-focused work documents the alignment gap directly: TukaBench (culturally grounded jailbreaks for African languages, arXiv:2606.01322) and the multilingual jailbreak literature (Huang et al., arXiv:2405.10936). Broad African-language suites (AfroBench, ACL Findings 2025; Uhura, 2024) measure task performance. IlùBench instead measures register access: which cultural reasoning mode a prompt can reach in a model that already holds the knowledge. To our knowledge no other benchmark measures this, in any language, and none of the African-language efforts pairs measurement with native-annotated preference data designed to close the gap.

## Citation

```bibtex
@misc{ilubench2026,
  title   = {Il\`uBench: Cultural Register Switching in Frontier Language Models},
  author  = {Chukwu, Chuma B.},
  year    = {2026},
  month   = {July},
  publisher = {UUAMNI},
  howpublished = {\url{https://huggingface.co/datasets/UUAMNI/ilubench}},
  note    = {v0.1. Protocol, seed probe set, and multi-model evidence, CC-BY-4.0}
}
```

*UUAMNI builds African-language preference data — annotated by native speakers, judged on cultural correctness — and the sovereign compute it trains on. Igbo first.*
