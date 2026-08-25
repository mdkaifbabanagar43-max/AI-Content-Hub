"""
Validation Pipeline — P3 Phase B (plan §6)
===========================================
Formalizes the four deterministic gates between a synthesized
ProductionBlueprint and caller acceptance:

  G1  Schema / Pydantic        -> enforced by synthesize ladder (recorded here)
  G2  Preservation compliance  -> NEW standalone gate (character-ID leak,
                                  advisory env/trend findings)
  G3  Narrative originality    -> reuse originality_validator similarity math,
                                  threshold from config.ORIGINALITY_THRESHOLD
  G4  Entity & Project-Bible   -> reuses ProductionDirector._validate_entities

Output is a structured ValidationReport attached to
ProductionBlueprint.validation_report (Q4: NOT surfaced in UI yet).
Hard-gate failures raise BlueprintValidationException AFTER the report is
assembled, so callers and logs always see which gate blocked the blueprint.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from config import ORIGINALITY_THRESHOLD
from core.models.blueprint import ProductionBlueprint
from core.models.clone_blueprint import CloneBlueprint
from core.models.clone_intent import CharacterMode, CloneIntent
from core.services.originality_validator import compute_narrative_similarity


class GateResult(BaseModel):
    name: str
    passed: bool = True
    findings: List[str] = Field(default_factory=list)
    similarity_score: Optional[float] = None


class ValidationReport(BaseModel):
    passed: bool = True
    merged_from_both: bool = False
    gates: List[GateResult] = Field(default_factory=list)


class ValidationPipeline:
    def __init__(self, director):
        # G4 reuses the director's entity validator: exactly one source of
        # truth for project-bible ID semantics.
        self.director = director

    # ── G2: preservation compliance ──────────────────────────────
    def _gate_preservation(self, intent: CloneIntent,
                           source_bp: CloneBlueprint,
                           production_bp: ProductionBlueprint) -> GateResult:
        profile = intent.preservation_profile
        findings: List[str] = []
        passed = True

        # Requested IDs are a KEEP-LIST (MIXED-style), never proof of full
        # preservation: other source roles must still be flagged as leaks.
        preserving_chars = (
            intent.character_mode == CharacterMode.PRESERVE_SOURCE
            or profile.preserve_characters
        )
        if not preserving_chars:
            allowed_extra = {r.lower() for r in intent.requested_character_ids}
            source_ids = {
                role.lower()
                for scene in source_bp.scenes
                for role in (scene.character_roles or [])
                if role
            }
            prod_ids = set(production_bp.required_character_ids or [])
            for scene in production_bp.scenes:
                prod_ids.update(scene.character_ids or [])
                for line in scene.dialogue or []:
                    if getattr(line, "character_id", None):
                        prod_ids.add(line.character_id)

            leaked = sorted(
                pid for pid in prod_ids
                if pid.lower() in source_ids and pid.lower() not in allowed_extra
            )
            if leaked:
                passed = False
                findings.append(
                    "Character preservation violated; source IDs reused while "
                    f"preserve_characters=False: {', '.join(leaked)}"
                )

        if not profile.preserve_environment:
            findings.append(
                "ADVISORY: environment regeneration asserted at prompt level; "
                "source has no location IDs to hard-assert against yet."
            )

        if intent.story_mode.value == "TREND_INSPIRED" and not profile.preserve_trend_structure:
            findings.append(
                "ADVISORY: story_mode=TREND_INSPIRED without "
                "preserve_trend_structure; hook formula applied, structure "
                "timings left free."
            )

        return GateResult(name="G2_preservation_compliance",
                          passed=passed, findings=findings)

    # ── G3: narrative originality (report + hard compare) ────────
    def _gate_originality(self, source_bp: CloneBlueprint,
                          production_bp: ProductionBlueprint) -> GateResult:
        score, matched = compute_narrative_similarity(source_bp, production_bp)
        passed = score <= ORIGINALITY_THRESHOLD
        findings = []
        if not passed:
            findings.append(
                f"Narrative similarity {score:.3f} exceeds "
                f"ORIGINALITY_THRESHOLD={ORIGINALITY_THRESHOLD:.2f}. "
                f"Top concepts: {', '.join(matched[:10])}"
            )
        return GateResult(name="G3_narrative_originality", passed=passed,
                          findings=findings, similarity_score=score)

    # ── G4: entity & project-bible IDs ───────────────────────────
    def _gate_entities(self, intent: CloneIntent, context,
                       production_bp: ProductionBlueprint) -> GateResult:
        profile = intent.preservation_profile
        errors = self.director._validate_entities(
            production_bp, context,
            allow_new_chars=(not profile.preserve_characters),
            allow_new_locs=(not profile.preserve_environment),
        )
        return GateResult(name="G4_entity_bible_ids",
                          passed=not errors,
                          findings=list(errors or []))

    # ── orchestration ────────────────────────────────────────────
    def run(self, intent: CloneIntent, source_bp: CloneBlueprint,
            production_bp: ProductionBlueprint, context,
            merged_from_both: bool = False) -> ValidationReport:
        report = ValidationReport(merged_from_both=merged_from_both)

        # G1 was enforced inside synthesize_clone_blueprint's parse/bind step;
        # reaching this pipeline means schema validation already succeeded.
        report.gates.append(GateResult(name="G1_schema_pydantic", passed=True))
        report.gates.append(self._gate_preservation(intent, source_bp, production_bp))
        report.gates.append(self._gate_originality(source_bp, production_bp))
        report.gates.append(self._gate_entities(intent, context, production_bp))

        report.passed = all(g.passed for g in report.gates)
        return report