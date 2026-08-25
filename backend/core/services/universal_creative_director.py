"""
UniversalCreativeDirector — P3 Phase B Boundary
================================================
Single transformation boundary per UNIVERSAL_TRANSFORMATION_CONTRACT:

    CloneIntent (+ SourceDNACluster) ──► UniversalCreativeDirector.transform()
                                         ──► validated ProductionBlueprint

Phase-B scope (plan §7 row B):
  - normalize_legacy(): ProductionTransformationRequest -> CloneIntent
    (permanent dual-accept per Q3; profile-wins rule tags MERGED_FROM_BOTH)
  - D3 MIXED degradation via effective_character_mode()
  - compiles the prompt through TransformationContext (NOT the director's
    inline builder), then delegates synthesis to
    ProductionDirector.synthesize_clone_blueprint() — engine/tasks untouched
  - runs the G1-G4 ValidationPipeline and attaches validation_report
  - does NOT replace the route yet (Phase C does that)

Legacy Trend Cloner adoption remains Phase F behind UCD_TREND_ENABLED.
"""
from typing import Optional, Tuple

from core.models.blueprint import ProductionBlueprint
from core.models.clone_blueprint import CloneBlueprint
from core.models.clone_intent import (
    CharacterMode,
    CreativeIntent,
    EnvironmentMode,
    StoryMode,
    CloneIntent,
    PreservationProfile,
    build_preservation_profile,
)
from core.models.context import GenerationContext
from core.models.dna import SourceDNACluster
from core.models.transformation import ProductionTransformationRequest
from core.models.transformation_context import (
    TransformationContext,
    effective_character_mode,
)
from core.services.production_director import (
    BlueprintValidationException,
    ProductionDirector,
    determine_story_complexity,
)
from core.services.source_dna_adapter import build_source_dna_cluster
from core.services.validation_pipeline import ValidationPipeline

_LEGACY_PRESERVATION_FLAGS = (
    "preserve_visual_style",
    "preserve_characters",
    "preserve_environment",
    "preserve_camera_pacing",
    "preserve_trend_structure",
    "preserve_structure",
    "preserve_pacing",
    "preserve_camera_language",
    "preserve_emotional_arc",
    "preserve_audio_style",
    "preserve_voice_style",
)


class UniversalCreativeDirector:
    def __init__(self, user_id: str = "", project_id: str = ""):
        # Kept for parity with ProductionDirector's constructor shape; the
        # authoritative identity always comes from the CloneIntent itself.
        self.user_id = user_id
        self.project_id = project_id
        self.director = ProductionDirector(user_id=user_id, project_id=project_id)
        self.context_compiler = TransformationContext()
        self.pipeline = ValidationPipeline(self.director)

    # ── normalization (Q3 permanent dual-accept) ─────────────────
    @staticmethod
    def normalize_legacy(request: ProductionTransformationRequest, *,
                         user_id: str, project_id: str,
                         source_video_id: Optional[str] = None
                         ) -> Tuple[CloneIntent, bool]:
        """
        Derives CloneIntent from a legacy-shaped request. Returns
        (intent, merged_from_both) where merged_from_both=True means BOTH the
        new preservation_profile block AND legacy top-level booleans were
        supplied — the profile wins (plan §5a conflict rule).
        """
        fields = getattr(request, "model_fields_set", set())
        has_profile_block = getattr(request, "preservation_profile", None) is not None
        merged = has_profile_block and any(
            f in fields for f in _LEGACY_PRESERVATION_FLAGS
        )

        # §5a conflict rule: when the caller supplied the new profile block,
        # it WINS outright — legacy top-level booleans are ignored (and the
        # merge is tagged via merged_from_both for telemetry).
        if has_profile_block:
            profile = request.preservation_profile
        else:
            profile_kwargs = {
                flag: getattr(request, flag)
                for flag in _LEGACY_PRESERVATION_FLAGS
                if flag in fields
            }
            profile = (
                build_preservation_profile(**profile_kwargs)
                if profile_kwargs else PreservationProfile()
            )

        creative = CreativeIntent(
            topic=request.topic or "Untitled concept",
            story_change=request.story_change,
            niche=request.niche or "General",
            language=request.language,
            tone=request.tone,
            target_duration_seconds=request.target_duration_seconds,
        )

        character_mode = (
            CharacterMode.PRESERVE_SOURCE if request.preserve_characters
            else CharacterMode.CREATE_NEW
        )
        environment_mode = (
            EnvironmentMode.PRESERVE_SOURCE if request.preserve_environment
            else EnvironmentMode.CREATE_NEW
        )
        if request.preserve_trend_structure:
            story_mode = StoryMode.TREND_INSPIRED
        elif request.preserve_structure is False:
            story_mode = StoryMode.NEW_STORY
        else:
            story_mode = StoryMode.STRUCTURE_INSPIRED

        intent = CloneIntent(
            user_id=user_id,
            project_id=project_id,
            source_video_id=source_video_id,
            preservation_profile=profile,
            character_mode=character_mode,
            environment_mode=environment_mode,
            story_mode=story_mode,
            creative_intent=creative,
            requested_character_ids=list(request.requested_character_ids),
            requested_location_ids=list(request.requested_location_ids),
            requested_prop_ids=list(request.requested_prop_ids),
            requested_style_id=request.requested_style_id,
            requested_voice_id=request.requested_voice_id,
        )
        return intent, merged

    # ── intent -> director-shaped request ────────────────────────
    @staticmethod
    def intent_to_request(intent: CloneIntent) -> ProductionTransformationRequest:
        """
        Recombines the profile into the five legacy booleans the synthesis
        ladder binds onto the blueprint (plan §5a reverse mapping):
          preserve_camera_pacing := camera_language OR pacing_editing
        """
        profile = intent.preservation_profile
        preserving_chars = (
            intent.character_mode == CharacterMode.PRESERVE_SOURCE
            or profile.preserve_characters
            or bool(intent.requested_character_ids)
        )
        return ProductionTransformationRequest(
            topic=intent.creative_intent.topic,
            story_change=intent.creative_intent.story_change,
            niche=intent.creative_intent.niche,
            target_duration_seconds=intent.creative_intent.target_duration_seconds,
            language=intent.creative_intent.language,
            tone=intent.creative_intent.tone,
            preserve_visual_style=profile.preserve_visual_style,
            preserve_characters=preserving_chars,
            preserve_environment=profile.preserve_environment,
            preserve_camera_pacing=(
                profile.preserve_camera_language or profile.preserve_pacing_editing
            ),
            preserve_trend_structure=(
                profile.preserve_trend_structure
                or intent.story_mode == StoryMode.TREND_INSPIRED
            ),
            clone_mode="custom",
            requested_character_ids=list(intent.requested_character_ids),
            requested_location_ids=list(intent.requested_location_ids),
            requested_prop_ids=list(intent.requested_prop_ids),
            requested_style_id=intent.requested_style_id,
            requested_voice_id=intent.requested_voice_id,
        )

    # ── the boundary ─────────────────────────────────────────────
    def transform(self, clone_blueprint: CloneBlueprint, *,
                  intent: Optional[CloneIntent] = None,
                  legacy_request: Optional[ProductionTransformationRequest] = None,
                  source_dna: Optional[SourceDNACluster] = None,
                  source_video_id: Optional[str] = None) -> ProductionBlueprint:
        if intent is None:
            if legacy_request is None:
                raise ValueError(
                    "transform() requires either `intent` or `legacy_request`."
                )
            intent, merged_from_both = self.normalize_legacy(
                legacy_request,
                user_id=clone_blueprint.user_id,
                project_id=clone_blueprint.project_id,
                source_video_id=source_video_id or clone_blueprint.source_video_id,
            )
        else:
            merged_from_both = False

        dna = source_dna or build_source_dna_cluster(clone_blueprint)
        prompt = self.context_compiler.compile_prompt(intent, dna)

        request = self.intent_to_request(intent)
        context = GenerationContext(
            user_id=intent.user_id,
            project_id=intent.project_id,
            job_id="ucd_transform_job",
        )
        target_dur = (
            request.target_duration_seconds
            or clone_blueprint.target_duration_seconds
        )
        scenes_cnt = (
            len(clone_blueprint.scenes)
            if (not request.target_duration_seconds
                or request.target_duration_seconds > 30.0)
            else None
        )
        complexity = determine_story_complexity(
            target_duration_seconds=target_dur,
            scene_count=scenes_cnt,
        )

        blueprint = self.director.synthesize_clone_blueprint(
            prompt=prompt,
            complexity=complexity,
            request=request,
            clone_blueprint=clone_blueprint,
            context=context,
        )

        report = self.pipeline.run(
            intent, clone_blueprint, blueprint, context,
            merged_from_both=merged_from_both,
        )
        blueprint.validation_report = report.model_dump()

        if not report.passed:
            errors = [
                f"{gate.name}: {finding}"
                for gate in report.gates if not gate.passed
                for finding in gate.findings
            ]
            raise BlueprintValidationException(
                "P3 validation pipeline rejected the synthesized blueprint.",
                errors=errors,
            )
        return blueprint