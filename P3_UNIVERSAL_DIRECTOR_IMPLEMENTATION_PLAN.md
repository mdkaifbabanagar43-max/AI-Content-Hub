# P3 IMPLEMENTATION PLAN — `CloneIntent` / `UniversalCreativeDirector` Convergence

**Status:** DRAFT FOR REVIEW — no code written yet
**Author:** Cline (ox-alpha)
**Date:** 2026-08-25
**Spec Sources:** `CANONICAL_CLONE_SCHEMA.md` v3.0.0 · `UNIVERSAL_TRANSFORMATION_CONTRACT.md`
**Governing Constraints:** MASTER_ARCHITECTURE_AUDIT.md Rules 1–3

---

## 1. Objective & Success Criteria

Converge the Video Cloner and Trend Cloner creative-transformation boundaries onto the
spec'd universal contract **without breaking either pipeline**, by:

1. Introducing `CloneIntent` (+ `PreservationProfile`, `CreativeIntent`, mode enums) as the
   canonical request object defined in `core/models/clone_intent.py`.
2. Introducing `core/services/universal_creative_director.py` as the single transformation
   boundary: `CloneIntent` + `SourceDNACluster` → validated `ProductionBlueprint`.
3. Mapping today's five boolean flags / four presets onto the eight-toggle
   `PreservationProfile` with **zero behavior change at default settings**.

| # | Success Criterion |
|---|---|
| S1 | All 33 existing regression tests pass unchanged through every phase |
| S2 | Legacy `/api/trend-cloner/*` routes remain 100% operational (Audit Rule 1) |
| S3 | `CanonicalGenerationEngine` receives byte-identical `ProductionBlueprint`s for equivalent requests (Audit Rule 3) |
| S4 | Old frontend payloads and new `preservation_profile` payloads produce equivalent blueprints |
| S5 | Narrative-originality gate (< 0.40) enforced on every transformation path, including Trend Cloner once adopted |

---

## 2. Current State vs Target State

```
CURRENT (Video Cloner)
Frontend ──► POST /projects/{pid}/clone-blueprints/{id}/transform
             body: ProductionTransformationRequest (5 flags + clone_mode preset)
                     │
                     ▼
             ProductionDirector.transform_clone_blueprint()
             ├─ _build_planning_context()      (Project Bibles)
             ├─ conditional prompt sections    (flag-driven, inline)
             ├─ _validate_entities()           (server-side ID checks)
             ├─ validate_blueprint_originality()
             └─ _estimate_costs()              → ProductionBlueprint (DRAFT)

CURRENT (Trend Cloner — legacy, Rule 1 protected)
Frontend ──► POST /api/trend-cloner/analyze|generate
             TrendAnalysis dict (ad-hoc) ──► trend_remixer ──► in-router Veo loop
             (no blueprints, no originality gate, no Cloud Tasks)

TARGET
Any caller ──► UniversalCreativeDirector.transform(intent: CloneIntent) -> ProductionBlueprint
                  │
                  ├─ CloneIntentNormalizer      (legacy shapes → CloneIntent)
                  ├─ SourceDNAClusterAdapter    (CloneBlueprint/SourceAnalysis/TrendAnalysis → 9 DNAs)
                  ├─ TransformationContext.compile_prompt()   (spec'd conditional assembly)
                  └─ 4-Gate ValidationPipeline:
                       G1 schema/pydantic → G2 preservation compliance →
                       G3 narrative originality (<0.40) → G4 entity/bible IDs
                     │
                     ▼
             ProductionBlueprint → (unchanged downstream: approve/generate/
             Cloud Tasks/worker/engine)
```

---

## 3. Design Decisions Requiring Sign-off

> Each decision lists a recommendation. Please veto/adjust before Phase A starts.

### D1 — API Contract Strategy: Superset Model on Existing Route ✅ recommended
Keep `POST .../transform` and its URL/semantics. Extend
`ProductionTransformationRequest` with **optional** new blocks
(`preservation_profile`, `character_mode/environment_mode/story_mode`,
`creative_intent`). A normalizer derives `CloneIntent` from whichever shape arrived
(new blocks win; legacy 5-flag path synthesizes an equivalent profile).
*Rejected alternative:* a v2 `/transform-intent` route — splits analytics, forces a
frontend cutover, zero functional gain at this stage.

### D2 — Eight-Toggle Profile Mapping (full matrix in §5)
All eight spec toggles implemented immediately; six already have live consumers or are
prompt-only. Two (`preserve_audio_style`, `preserve_voice_style`) are
**prompt-influential only** today — they inject directives but no audio-pipeline
switch exists yet; documented as forward-compatible no-ops with telemetry.

### D3 — Mode Enums Now, `MIXED` Degraded ⚠️ your call
`CharacterMode.PRESERVE_SOURCE/CREATE_NEW`, `EnvironmentMode.*`, and
`StoryMode.NEW_STORY/STRUCTURE_INSPIRED/TREND_INSPIRED` map cleanly to booleans.
`MIXED` requires per-character selection UI that doesn't exist. Recommendation:
accept & store `MIXED` but normalize it to *PRESERVE_SOURCE ∩ requested_character_ids*
until the picker ships — identical output to today's
`requested_character_ids ⇒ preserve_characters=True` alias rule.

### D4 — DNA Adapter Location & Completeness
New `core/models/dna.py` (9 spec models verbatim) +
`core/services/source_dna_adapter.py` exposing
`build_source_dna_cluster(clone_blueprint) -> SourceDNACluster`. Every DNA is
derivable from existing persisted data:

| DNA | Existing source fields |
|---|---|
| VisualStyleDNA | `SourceVisualStyle.{art_style, visual_style_summary→render_language, lighting_summary, color_tone→color_palette, realism_level}` |
| CharacterDNA | `semantic_scenes[].character_roles` + counts; descriptions from `visual_style.character_design` |
| EnvironmentDNA | `semantic_scenes[].{location_summary→setting_type, lighting_summary→environmental_mood}` |
| CameraDNA | `semantic_scenes[].shot_type → dominant_shot_types`; `.camera_motion → motion_styles` |
| PacingDNA | `PacingProfile` (avg/fastest/slowest shot dur, rhythm, intensity) |
| EditingDNA | `semantic_scenes[].transition` histogram; framing from shot-type variance |
| AudioDNA | `SourceAudioProfile.{has_speech→has_speech, has_background_music→has_bgm, music_mood, sfx_present→sfx_density}` |
| NarrativeStructureDNA | `HookAnalysis.{hook_start/end_seconds→hook_duration_seconds, confidence→hook_intensity}` + `NarrativeBeat[]` (total_beats, beat_types, climax %) |
| TrendDNA | Trend Cloner only: `TrendAnalysis.{humor_mechanism→viral_hook_type}`, pacing archetype from `pacing_scenes` |

**Strict Narrative Separation (schema §3) enforced by construction:** the adapter never
copies `transcript_text`, `dialogue_beats[].text`, `visual_action`, or beat
`description` strings into any DNA handed to the LLM — structure/timings only.

### D5 — UCD Wraps, Then Strangles `ProductionDirector` ✅ recommended
`UniversalCreativeDirector.transform()` owns intent normalization, DNA cluster build,
`TransformationContext.compile_prompt()` (moved out of ProductionDirector's inline
sections), and Gates G2–G4 orchestration. Story-synthesis invocation + retry ladder +
cost estimates stay in ProductionDirector methods, which UCD calls — so
`generate_blueprint()` (idea-first path) keeps working unchanged.
Engine, tasks, worker: **untouched** (Rule 3).

### D6 — Trend Cloner Adoption Deferred to Phase F, Behind Flag
Phase F adds an adapter (`TrendAnalysis + GenerateRequest → CloneIntent`) and swaps
trend_cloner's internal remix step to UCD behind `UCD_TREND_ENABLED=0`
(default-off env flag). Routes, request models, and the in-router execution loop stay
byte-identical until you approve the flip in a separate mini-review.
Audit Rule 1 is never at risk.

---

## 4. New Artifacts

| Path | Responsibility |
|---|---|
| `backend/core/models/dna.py` | 9 DNA models + `SourceDNACluster` (spec §2 verbatim) |
| `backend/core/models/clone_intent.py` | `CloneIntent`, `PreservationProfile`, `CreativeIntent`, 3 mode enums (spec §1 + D3 note) |
| `backend/core/models/transformation_context.py` | `TransformationContext.compile_prompt()` (contract §1) |
| `backend/core/services/universal_creative_director.py` | Boundary class: normalize → adapt → compile → delegate synthesis → run Gates |
| `backend/core/services/source_dna_adapter.py` | CloneBlueprint / SourceAnalysis / TrendAnalysis → `SourceDNACluster` |
| `backend/core/services/validation_pipeline.py` | G1–G4 gate runner returning structured `ValidationReport` |
| `backend/tests/test_clone_intent_mapping.py` | Table-driven parity tests for §5 matrix |
| `backend/tests/test_universal_creative_director.py` | Normalization, gate ordering, separation guarantee |
| `P3_UNIVERSAL_DIRECTOR_IMPLEMENTATION_PLAN.md` | This document (committed for traceability) |

**Modified files:** `core/models/transformation.py` (optional new blocks +
bidirectional alias validator), `core/services/production_director.py`
(extract prompt-section builders for reuse), `routers/video_cloner.py`
(transform handler delegates to UCD), `.clinerules` (reference new boundary
once merged).

---

## 5. Preservation Flag Mapping Matrix (heart of this review)

### 5a. Field-by-field: legacy → `PreservationProfile`

| Legacy input (today) | New profile field(s) | Default parity | Notes |
|---|---|:-:|---|
| `preserve_visual_style` (bool, T) | `preserve_visual_style` | T | direct |
| `preserve_characters` (bool, F) | `preserve_characters` | F | direct; still force-set when `requested_character_ids` present |
| `preserve_environment` (bool, F) | `preserve_environment` | F | direct |
| `preserve_camera_pacing` (bool, T) | split → `preserve_camera_language` **AND** `preserve_pacing_editing` | T/T | one legacy toggle controlled two spec toggles; normalizer sets both from the single bit |
| `preserve_trend_structure` (bool, F) | `preserve_trend_structure` | F | also implied by `story_mode=TREND_INSPIRED` |
| *(no legacy source)* | `preserve_audio_style` | F | prompt-directive only — forward-compat no-op |
| *(no legacy source)* | `preserve_voice_style` | F | prompt-directive only — forward-compat no-op |
| `preserve_structure` (granular, T) | folded into `story_mode` | — | True → `STRUCTURE_INSPIRED` when story isn't brand-new |
| `preserve_pacing` / `preserve_camera_language` (granular) | same two split targets above | T | OR-ed with primary bits |
| `preserve_emotional_arc` (granular, T) | folded into pacing directive text | — | no independent consumer exists today |

**Conflict rule:** if `preservation_profile` AND any legacy top-level boolean are both
present, **profile wins**, and a `MERGED_FROM_BOTH` telemetry note is recorded.
Never silently average.

### 5b. Preset parity check (contract §3 vs current `clone_mode`)

| Contract preset | Backend `clone_mode` today | Parity |
|---|---|:-:|
| Style Clone | `style_only` | ✅ exact |
| Character Clone | — | ❌ **missing** → add `characters_only` preset |
| Style + Characters | `characters_and_style` | ✅ exact |
| Full Visual Clone | `full_visual_clone` | ✅ exact |
| Trend Inspired | `trend_inspired` | ✅ exact |

Adding `characters_only` (chars ✅ · style ✅ · camera ✖ · pacing ✖ · env ✖ · trend ✖)
closes the only spec gap; frontend `applyPreset` union gains one member in Phase D.

---

## 6. Validation Pipeline (formalizing what exists + one new gate)

| Gate | Status today | Work required |
|---|---|---|
| G1 Schema/Pydantic | exists (retry-on-fail ladder) | unchanged |
| G2 Preservation compliance | partial (`allow_new_chars/locs` inside `_validate_entities`) | extract as standalone gate; char-ID leak assert reused from originality_validator; NEW environment/location asserts driven by profile |
| G3 Originality < 0.40 | exists (`originality_validator`) | reused verbatim |
| G4 Entity/Bible IDs | exists (`_validate_entities`, MISSING_ASSET sentinels) | moved behind gate interface, logic unchanged |

`ValidationReport {gate, passed, findings[], similarity_score?}` attaches to blueprint
metadata (`blueprint.validation_report`) for diagnostics and future Step-4 UI display.

---

## 7. Migration Sequencing (each phase shippable & revertible independently)

| Phase | Scope | Exit criteria |
|---|---|---|
| **A. Foundation** | `dna.py`, `clone_intent.py`, source DNA adapter + unit tests; **nothing wired** | New tests green; all 33 legacy tests untouched-green; adapter round-trips every fixture CloneBlueprint |
| **B. Boundary** | UCD + TransformationContext + validation_pipeline wrapping ProductionDirector; still no route change (direct-instantiation tests only) | Golden dual-run: blueprints produced via UCD are structurally equivalent (scene count, durations ±ε, entity IDs) to direct director calls under identical mocked LLM responses |
| **C. Route Switch** | `video_cloner.py` transform handler delegates to UCD; normalizer accepts both payload shapes | Scripted dual-run diff over 5 fixtures: old-shape→old-code ≡ new-shape→UCD; full suite green |
| **D. Frontend opt-in** | VideoCloner sends `preservation_profile` alongside legacy booleans for one release (dual-send); adds `characters_only` preset | tsc clean; wizard visually unchanged; backend telemetry confirms profile received |
| **E. Cleanup** | Drop dual-send; legacy booleans deprecated-but-accepted; docs updated | Deprecation notes in logs/docs only; suite green |
| **F. Trend Cloner** | trend adapter + UCD behind `UCD_TREND_ENABLED=0` default-off | Flag-off: byte-identical behavior (regression suite proves it). Flip happens in a separate approved review |

**Rollback:** any phase = revert its commit. No data migrations — new types are
request-time constructs; the only persisted addition is optional blueprint metadata.

---

## 8. Test Strategy Highlights

- **Parity-table tests:** every §5a row becomes a parametrized case asserting
  normalizer output — contract drift becomes a test failure forever.
- **Separation-guarantee test:** fixture transcripts/dialogue sampled as forbidden
  substrings; adapter output scanned — schema §3 made executable.
- **AST literal scan extended:** `universal_creative_director.py`,
  `source_dna_adapter.py`, `validation_pipeline.py` added to
  `test_model_routing.files_to_check`.
- **Golden dual-run harness (Phases B/C):** frozen mock LLM responses replayed through
  old-path vs new-path; structural deep-diff gates the merge.
- **Standing rule:** all 33 existing tests green at every phase commit (S1).

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Prompt-text drift subtly changes LLM outputs | Med | Frozen-response golden dual-runs gate on structure, not prose |
| Dual-shape ambiguity (profile + legacy booleans conflict) | Med | Explicit precedence rule + `MERGED_FROM_BOTH` telemetry (§5a) |
| Trend Cloner regression despite Rule 1 care | Low | Default-off flag, dedicated regression suite, separate flip review |
| `MIXED` mode over-promising | Low | Accept-and-degrade per D3; documented limitation |
| Scope creep into engine/tasks/worker | Low | Audit Rule 3 guard: those modules appear in zero P3 commits |

## 10. Open Questions for Reviewer

1. **D3** — OK to accept-and-degrade `MIXED` now, real per-character selection later?
2. **§5b** — Approve adding the missing `characters_only` preset?
3. **Phase E** — eventually hard-delete legacy top-level booleans, or permanent dual-accept?
4. Surface `ValidationReport` in the Step-4 Storyboard UI during this effort, or defer?
5. Keep originality threshold 0.40 hardcoded in the gate, or expose it as a config
   constant next to `MAX_SCENE_QUALITY_RETRIES`?

## 11. Explicit Non-Goals

- Any modification to `CanonicalGenerationEngine`, `core/tasks.py`, or worker endpoints
- Removing or reshaping any existing route/URL
- Per-character MIXED selection UI
- Audio-pipeline switches behind the two forward-compat toggles
- Billing/pricing changes

