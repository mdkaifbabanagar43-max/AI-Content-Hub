# GOLDEN TEST MATRIX — CLONEFRAME UNIVERSAL ENGINE

**Canonical Golden Fixture:** `videos/WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4`  
**Test Suite Target:** `backend/tests/test_universal_clone_golden.py`  

---

## 1. Golden Test Suite (Tests A – H)

```
========================================================================================
TEST ID   TEST NAME                 INPUT / PRESERVATION POLICY      EXPECTED OUTCOME
========================================================================================
TEST A    Style Clone Only          preserve_visual_style=True       ✅ Visual style & lighting match
                                    preserve_characters=False        ✅ Brand new character IDs generated
                                    preserve_environment=False       ✅ Brand new environment settings
                                    story_mode=NEW_STORY             ✅ Originality score < 0.20

TEST B    Character Clone Only      preserve_visual_style=False      ✅ Source character appearance kept
                                    preserve_characters=True         ✅ Source character IDs reused
                                    story_mode=NEW_STORY             ✅ Brand new story actions & dialogue

TEST C    Style + Characters        preserve_visual_style=True       ✅ Source art style + characters kept
                                    preserve_characters=True         ✅ New environment created
                                    preserve_environment=False       ✅ New bank heist story created
                                    story_mode=NEW_STORY             ✅ Originality score < 0.20

TEST D    Full Visual Clone         preserve_visual_style=True       ✅ Source art style kept
                                    preserve_characters=True         ✅ Source characters kept
                                    preserve_environment=True        ✅ Source visual world setting kept
                                    story_mode=NEW_STORY             ✅ Brand new narrative actions

TEST E    Trend Inspired            story_mode=TREND_INSPIRED        ✅ TrendDNA hook & rhythm used
                                    preserve_characters=False        ✅ Brand new characters generated
                                    preserve_visual_style=False      ✅ Original plot text 0% copied

TEST F    Originality Rejection     Malicious/Defective prompt       ❌ MUST RAISE OriginalityValidationException
                                    attempting verbatim plot clone   ❌ Similarity score > 0.40 rejected

TEST G    Schema Compatibility      Legacy frontend payload          ✅ Auto-maps `target_topic` -> `topic`
                                    vs Canonical CloneIntent         ✅ Both yield identical ProductionBlueprint

TEST H    Failure Isolation         Mocked Veo / Provider 500 error  ✅ Job marked FAILED (no stuck state)
                                                                     ✅ 100% credits refunded atomically
                                                                     ✅ Zero duplicate retry tasks enqueued
========================================================================================
```

---

## 2. Invariant Assertions Required for Every Test

1. **Deterministic Execution:** Zero paid external credits consumed during automated test suite runs (mocked provider boundaries).
2. **Schema Validity:** Every generated blueprint must parse cleanly into `ProductionBlueprint` with zero Pydantic validation errors.
3. **Lineage Binding:** Every blueprint must store `source_clone_blueprint_id`, `blueprint_version`, and `preservation_profile`.
4. **Idempotent Billing:** Credit reservation and deduction must balance to exactly $0.00 / 0 credits on failed runs.
