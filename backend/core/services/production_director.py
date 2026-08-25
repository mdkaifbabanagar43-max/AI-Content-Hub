import re
import json
import datetime
import uuid
from typing import Optional, List, Dict
from pydantic import ValidationError

from config import ModelRoutingConfig
from core.models.blueprint import ProductionBlueprint, SceneBlueprint
from core.models.context import GenerationContext
from core.models.clone_blueprint import CloneBlueprint
from core.models.transformation import ProductionTransformationRequest
from core.services.bible_loader import ProjectBibleLoader
from core.repositories.blueprint_repo import BlueprintRepository
from core.services.originality_validator import (
    validate_blueprint_originality,
    OriginalityValidationException
)
from services.ai_service import get_gemini_client

def _clean_and_parse_json(raw_text: str) -> dict:
    """Robustly extracts and parses JSON from model responses (Gemini or Claude)."""
    if not raw_text:
        raise ValueError("Model returned empty structured output response")
    cleaned = re.sub(r'```json|```', '', raw_text).strip()
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    if start_idx != -1 and end_idx != -1:
        cleaned = cleaned[start_idx:end_idx+1]
    return json.loads(cleaned)

def determine_story_complexity(
    target_duration_seconds: Optional[float] = None,
    scene_count: Optional[int] = None,
    requested_character_count: Optional[int] = None,
    is_complex_flag: Optional[bool] = None
) -> str:
    """
    Deterministic rule engine to classify story generation complexity.
    Returns 'NORMAL' or 'COMPLEX'.
    
    Rules for COMPLEX story:
    1. Explicit flag is True
    2. Long duration: target_duration_seconds > 30.0s
    3. Multi-beat structure: scene_count > 4
    4. Ensemble cast: requested_character_count >= 3
    """
    if is_complex_flag:
        return "COMPLEX"
    if target_duration_seconds is not None and target_duration_seconds > 30.0:
        return "COMPLEX"
    if scene_count is not None and scene_count > 4:
        return "COMPLEX"
    if requested_character_count is not None and requested_character_count >= 3:
        return "COMPLEX"
    return "NORMAL"

class BlueprintValidationException(Exception):
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []

class MissingAssetException(Exception):
    def __init__(self, asset_type: str, description: str, scene_id: str):
        super().__init__(f"Missing Asset: {asset_type} ({description}) in scene {scene_id}")
        self.payload = {
            "type": "MISSING_ASSET",
            "asset_type": asset_type,
            "description": description,
            "scene_id": scene_id
        }

class ProductionDirector:
    def __init__(self, user_id: str, project_id: str):
        self.user_id = user_id
        self.project_id = project_id
        self.repo = BlueprintRepository()
        self.bible_loader = ProjectBibleLoader()

    def _build_planning_context(self, context: GenerationContext) -> str:
        """Loads canonical Bibles to inform the AI Director."""
        bibles = self.bible_loader.load_all_bibles(context)
        
        ctx_str = f"Project Context for ID: {self.project_id}\n\n"
        
        # Load Characters
        ctx_str += "AVAILABLE CHARACTERS:\n"
        for cb in bibles.get("characters", []):
            ctx_str += f"- ID: {cb.character_id} | Name: {cb.name}\n"
            
        ctx_str += "\nAVAILABLE LOCATIONS:\n"
        for lb in bibles.get("locations", []):
            ctx_str += f"- ID: {lb.location_id} | Name: {lb.name}\n"
            
        ctx_str += "\nAVAILABLE VOICES:\n"
        for vb in bibles.get("voices", []):
            ctx_str += f"- ID: {vb.voice_id} | Character ID: {vb.character_id}\n"
            
        ctx_str += "\nAVAILABLE PROPS:\n"
        for pb in bibles.get("props", []):
            ctx_str += f"- ID: {pb.prop_id} | Name: {getattr(pb, 'name', 'Unknown')}\n"
            
        ctx_str += "\nAVAILABLE STYLES:\n"
        for sb in bibles.get("styles", []):
            ctx_str += f"- ID: {sb.style_id} | Name: {getattr(sb, 'name', 'Unknown')}\n"
            
        return ctx_str

    def _estimate_costs(self, blueprint: ProductionBlueprint):
        """Calculates rough planning estimates clearly marked as ESTIMATE."""
        total_video_s = 0.0
        total_chars = 0
        veo_attempts = 0
        
        for s in blueprint.scenes:
            total_video_s += s.estimated_duration_seconds
            veo_attempts += (blueprint.quality_strategy.max_retries if blueprint.quality_strategy else 1)
            for d in s.dialogue:
                total_chars += len(d.text)
                
        blueprint.estimated_video_seconds = total_video_s
        blueprint.estimated_dialogue_characters = total_chars
        blueprint.estimated_generation_attempts = veo_attempts
        blueprint.estimated_reference_assets = len(blueprint.required_character_ids) + len(blueprint.required_location_ids)
        blueprint.estimate_generated_at = datetime.datetime.now(datetime.timezone.utc)
        
        # Pricing logic (ESTIMATE ONLY - not actual provider billing guarantee)
        # ElevenLabs ~= $0.00015/char, Veo ~= $0.50/generation
        cost_audio = total_chars * 0.00015
        cost_video = veo_attempts * 0.50
        blueprint.estimated_cost_usd = round(cost_audio + cost_video, 2)

    def _validate_entities(self, blueprint: ProductionBlueprint, context: GenerationContext, allow_new_chars: bool = False, allow_new_locs: bool = False) -> List[str]:
        """
        Server-side independent validation of all Bible IDs and project scoping.
        Never trusts the LLM.
        """
        errors = []
        bibles = self.bible_loader.load_all_bibles(context)
        custom_chars = {b.character_id for b in bibles.get("characters", [])}
        custom_locs = {b.location_id for b in bibles.get("locations", [])}
        custom_props = {b.prop_id for b in bibles.get("props", [])}
        custom_voices = {b.voice_id for b in bibles.get("voices", [])}
        custom_styles = {b.style_id for b in bibles.get("styles", [])}

        valid_chars = custom_chars
        valid_locs = custom_locs
        valid_props = custom_props
        valid_styles = custom_styles
        valid_voices = (custom_voices | {"default_voice", "default", "voice_default", "none", None}) if custom_voices else set()
        all_valid_entity_ids = valid_chars | valid_locs | valid_props
        
        def _check_missing_asset(entity_id: Optional[str], default_scene_id: str = "global"):
            if entity_id and isinstance(entity_id, str) and entity_id.startswith("MISSING_ASSET:"):
                parts = entity_id.split(":")
                asset_type = parts[1] if len(parts) > 1 else "UNKNOWN"
                desc = parts[2] if len(parts) > 2 else "Unknown"
                scene_id = parts[3] if len(parts) > 3 else default_scene_id
                raise MissingAssetException(asset_type, desc, scene_id)
        
        # 1. Blueprint-level entity checks
        for c_id in blueprint.required_character_ids:
            _check_missing_asset(c_id)
            if not allow_new_chars and valid_chars and c_id not in valid_chars:
                errors.append(f"Missing character: {c_id}")
        for l_id in blueprint.required_location_ids:
            _check_missing_asset(l_id)
            if not allow_new_locs and valid_locs and l_id not in valid_locs:
                errors.append(f"Missing location: {l_id}")
        for p_id in blueprint.required_prop_ids:
            _check_missing_asset(p_id)
            if valid_props and p_id not in valid_props:
                errors.append(f"Missing prop: {p_id}")
                
        if blueprint.visual_style_id:
            _check_missing_asset(blueprint.visual_style_id)
            if valid_styles and blueprint.visual_style_id not in valid_styles:
                errors.append(f"Missing style: {blueprint.visual_style_id}")
            
        if blueprint.audio_strategy and blueprint.audio_strategy.primary_voice_id:
            if valid_voices and blueprint.audio_strategy.primary_voice_id not in valid_voices:
                errors.append(f"Missing primary voice: {blueprint.audio_strategy.primary_voice_id}")
            
        # 2. Scene-level entity & duration checks
        scene_ids = set()
        for s in blueprint.scenes:
            if s.scene_id in scene_ids:
                errors.append(f"Duplicate scene ID: {s.scene_id}")
            scene_ids.add(s.scene_id)
            
            if s.estimated_duration_seconds <= 0:
                errors.append(f"Invalid duration in scene {s.scene_id}")
                
            for c_id in s.character_ids:
                _check_missing_asset(c_id, s.scene_id)
                if not allow_new_chars and valid_chars and c_id not in valid_chars:
                    errors.append(f"Scene {s.scene_id} character missing: {c_id}")
                    
            if s.location_id:
                _check_missing_asset(s.location_id, s.scene_id)
                if not allow_new_locs and valid_locs and s.location_id not in valid_locs:
                    errors.append(f"Scene {s.scene_id} location missing: {s.location_id}")
                
            for p_id in s.prop_ids:
                _check_missing_asset(p_id, s.scene_id)
                if valid_props and p_id not in valid_props:
                    errors.append(f"Scene {s.scene_id} prop missing: {p_id}")
                    
            if s.primary_reference_asset_id:
                _check_missing_asset(s.primary_reference_asset_id, s.scene_id)
                if not allow_new_chars and not allow_new_locs and all_valid_entity_ids and s.primary_reference_asset_id not in all_valid_entity_ids:
                    errors.append(f"Scene {s.scene_id} primary reference asset missing: {s.primary_reference_asset_id}")
                
            for req in s.continuity_requirements:
                if not allow_new_chars and not allow_new_locs and all_valid_entity_ids and req.asset_id not in all_valid_entity_ids:
                    errors.append(f"Scene {s.scene_id} continuity asset missing: {req.asset_id}")
            
            for d in s.dialogue:
                if not allow_new_chars and valid_chars and d.character_id not in valid_chars:
                    errors.append(f"Dialogue character missing: {d.character_id}")
                if valid_voices and d.voice_id not in valid_voices:
                    errors.append(f"Dialogue voice missing: {d.voice_id}")
                if d.estimated_duration_seconds <= 0:
                    errors.append(f"Dialogue in scene {s.scene_id} has non-positive duration")
                
        return errors

    def _invoke_story_model(self, prompt: str, complexity: str = "NORMAL") -> str:
        """Invokes the appropriate model (Gemini or Claude Bedrock) based on story complexity."""
        model_name = ModelRoutingConfig.COMPLEX_STORY if complexity == "COMPLEX" else ModelRoutingConfig.NORMAL_STORY
        
        if "claude" in model_name.lower():
            from services.ai_service import _invoke_bedrock_claude
            return _invoke_bedrock_claude(prompt, model_name, temperature=0.2)
        else:
            client = get_gemini_client()
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProductionBlueprint
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            return response.text

    def generate_blueprint(self, user_idea: str, target_duration: float) -> ProductionBlueprint:
        context = GenerationContext(user_id=self.user_id, project_id=self.project_id, job_id="planning_job")
        planning_context = self._build_planning_context(context)
        complexity = determine_story_complexity(target_duration_seconds=target_duration)
        
        prompt = f"""
        You are an AI Production Director.
        Create a detailed cinematic ProductionBlueprint based on this concept:
        
        USER IDEA: {user_idea}
        TARGET DURATION: {target_duration} seconds
        
        Use the provided Project Context to assign REAL Canonical IDs (Characters, Locations, Voices, Props, Styles).
        DO NOT invent new IDs if they do not exist in the context.
        
        REQUIREMENTS:
        - Divide the story into logical sequential scenes.
        - Assign varied, cinematic camera direction (shot_type, motion, lens).
        - Provide continuity constraints (e.g., character holding prop).
        - Provide estimated dialogue seconds (rough estimate).
        - Ensure total scene durations approximate {target_duration}s.
        
        {planning_context}
        """
        
        max_retries = 2
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    retry_prompt = prompt + f"\n\nYOUR PREVIOUS ATTEMPT FAILED WITH ERROR:\n{last_error}\nPlease fix the schema issues and try again."
                else:
                    retry_prompt = prompt
                
                raw_json = self._invoke_story_model(retry_prompt, complexity=complexity)
                blueprint_data = _clean_and_parse_json(raw_json)
                blueprint = ProductionBlueprint(**blueprint_data)
                
                # Overwrite and enforce internal project bindings & identity
                blueprint.project_id = self.project_id
                if not blueprint.blueprint_id:
                    blueprint.blueprint_id = f"bp_{uuid.uuid4().hex[:8]}"
                
                # Validation Step 1: Entity References
                entity_errors = self._validate_entities(blueprint, context)
                if entity_errors:
                    raise BlueprintValidationException("Entity validation failed.", errors=entity_errors)
                
                # Validation Step 2: Dialogue vs Scene Duration Warning
                for s in blueprint.scenes:
                    dial_dur = sum(d.estimated_duration_seconds for d in s.dialogue)
                    if dial_dur > s.estimated_duration_seconds:
                        print(f"DURATION_WARNING: Scene {s.scene_id} dialogue ({dial_dur}s) exceeds scene duration ({s.estimated_duration_seconds}s).")
                
                # Step 3: Cost Estimates
                self._estimate_costs(blueprint)
                
                # Save version 1 with READY_FOR_APPROVAL status (never auto-approved)
                blueprint.blueprint_version = 1
                blueprint.status = "READY_FOR_APPROVAL"
                self.repo.save(self.user_id, blueprint)
                
                return blueprint
                
            except (ValidationError, json.JSONDecodeError, ValueError) as pyd_err:
                last_error = str(pyd_err)
                print(f"Schema / JSON Validation failed on attempt {attempt}: {last_error}")
            except BlueprintValidationException as val_err:
                last_error = f"{val_err}: {val_err.errors}"
                print(f"Blueprint Entity Validation failed on attempt {attempt}: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"Unknown generation error on attempt {attempt}: {last_error}")
                
        raise Exception(f"Failed to generate valid ProductionBlueprint after {max_retries} retries. Last error: {last_error}")

    def transform_clone_blueprint(
        self, clone_blueprint: CloneBlueprint, request: ProductionTransformationRequest
    ) -> ProductionBlueprint:
        context = GenerationContext(user_id=self.user_id, project_id=self.project_id, job_id="transform_job")
        planning_context = self._build_planning_context(context)
        
        target_dur = request.target_duration_seconds or clone_blueprint.target_duration_seconds
        scenes_cnt = len(clone_blueprint.scenes) if (not request.target_duration_seconds or request.target_duration_seconds > 30.0) else None
        char_cnt = len(request.requested_character_ids) if request.requested_character_ids else 0
        
        complexity = determine_story_complexity(
            target_duration_seconds=target_dur,
            scene_count=scenes_cnt,
            requested_character_count=char_cnt
        )

        user_topic = request.topic or "Fresh original story"
        story_change = request.story_change or "Invent a new, engaging, humorous or dramatic narrative"
        tone = request.tone or "Engaging"
        language = request.language or "English"

        # User-Controlled Preservation Directives
        preserve_style = request.preserve_visual_style
        preserve_chars = request.preserve_characters
        preserve_env = request.preserve_environment
        preserve_pacing = request.preserve_camera_pacing
        preserve_trend = request.preserve_trend_structure or (request.clone_mode == "trend_inspired")

        # 1. Visual Style DNA
        visual_style = clone_blueprint.visual_style_profile
        art_style = getattr(visual_style, 'art_style', "3D digital animation") if visual_style else "3D digital animation"
        lighting = getattr(visual_style, 'lighting_summary', None) or getattr(visual_style, 'lighting', "Cinematic lighting") if visual_style else "Cinematic lighting"
        color_palette = getattr(visual_style, 'color_tone', None) or getattr(visual_style, 'color_palette', "Vibrant") if visual_style else "Vibrant"
        render_language = getattr(visual_style, 'visual_style_summary', None) or getattr(visual_style, 'render_language', "3D digital render") if visual_style else "3D digital render"

        if preserve_style:
            style_instruction = f"""
        SOURCE VISUAL STYLE (MANDATORY TO PRESERVE):
        - Art Style: {art_style}
        - Lighting & Ambiance: {lighting}
        - Color Palette: {color_palette}
        - Render Language: {render_language}
        - Aspect Ratio: {clone_blueprint.aspect_ratio}
        """
        else:
            style_instruction = f"""
        VISUAL STYLE POLICY:
        - DO NOT preserve the source video's visual art style.
        - INVENT a fresh, fitting visual art style tailored specifically to the new story topic ({user_topic}).
        """

        # 2. Character DNA
        if preserve_chars:
            character_design = getattr(visual_style, 'character_design', "Stylized characters") if visual_style else "Stylized characters"
            char_instruction = f"""
        SOURCE CHARACTERS (PRESERVE EXACT APPEARANCE):
        - Character Visual Design: {character_design}
        - Keep the exact physical appearance and character designs from source.
        """
        else:
            char_instruction = f"""
        CHARACTER POLICY (DO NOT REUSE SOURCE CHARACTERS):
        - DO NOT reuse source character identities, descriptions, or source character IDs.
        - INVENT brand new original characters appropriate for the new story ({user_topic}).
        - Use new character IDs like 'char_lead_1', 'char_secondary_1'.
        """

        # 3. Environment DNA
        if preserve_env:
            env_instruction = """
        ENVIRONMENT (PRESERVE SOURCE WORLD):
        - Keep the general world environment and aesthetic from the source video.
        """
        else:
            env_instruction = f"""
        ENVIRONMENT POLICY:
        - Create NEW settings, locations, and backgrounds appropriate for the new story ({user_topic}).
        - Do not reuse source specific locations.
        """

        # 4. Pacing & Camera DNA
        if preserve_pacing:
            pacing = clone_blueprint.pacing_profile
            rhythm = getattr(pacing, 'rhythm_description', "Dynamic narrative pacing") if pacing else "Dynamic narrative pacing"
            avg_shot_dur = getattr(pacing, 'average_shot_duration', 4.0) if pacing else 4.0
            intensity = getattr(pacing, 'overall_intensity', "Medium") if pacing else "Medium"
            pacing_instruction = f"""
        PACING & CAMERA LANGUAGE (PRESERVE RHYTHM):
        - Pacing Rhythm: {rhythm} (Average shot duration: {avg_shot_dur:.1f}s, Intensity: {intensity})
        - Match the source pacing rhythm and cinematic camera motion styles.
        """
        else:
            pacing_instruction = f"""
        PACING & CAMERA LANGUAGE:
        - Use standard cinematic pacing tailored for a short-form video of ~{target_dur}s.
        """

        trend_instruction = ""
        if preserve_trend:
            trend_instruction = """
        TREND INSPIRED HOOK & RETENTION:
        - Apply high-retention viral pacing: explosive 0-3s hook, rapid escalation curve, and sharp punchy climax.
        """

        prompt = f"""
        You are an AI Production Director creating a NEW ORIGINAL STORYBOARD based on USER CREATIVE INTENT and USER PRESERVATION CHOICES.
        
        CRITICAL NARRATIVE SEPARATION DIRECTIVE:
        - DO NOT copy, summarize, or reproduce the source video's plot, dialogue, action sequence, scene order, or punchline.
        - CREATE a materially DIFFERENT narrative driven entirely by the User Transformation Request below.
        
        USER CREATIVE INTENT (PRIMARY NARRATIVE DRIVER):
        - New Story Topic: {user_topic}
        - New Story Action / Changes: {story_change}
        - Tone / Mood: {tone}
        - Language: {language}
        - Target Duration: {target_dur}s
        
        {style_instruction}
        {char_instruction}
        {env_instruction}
        {pacing_instruction}
        {trend_instruction}
        
        REQUESTED ASSETS (You must use these if provided, or select appropriately from Project Context):
        - Style ID: {request.requested_style_id}
        - Character IDs: {request.requested_character_ids}
        - Voice ID: {request.requested_voice_id}
        - Location IDs: {request.requested_location_ids}
        - Prop IDs: {request.requested_prop_ids}
        
        {planning_context}
        
        INSTRUCTIONS:
        1. CREATE A BRAND NEW STORY: Invent new character motivations, new conflict, new actions, and new comedic/dramatic resolution matching the User Creative Intent. Do NOT reuse the source video's story events.
        2. RESPECT PRESERVATION POLICIES:
           - If Characters are preserved, keep source character designs. If NOT preserved, invent brand new characters.
           - If Style is preserved, keep authoritative art style. If NOT preserved, create a fitting new style.
        3. Assign appropriate entity IDs (Characters, locations, props, voices). If no assets exist in Project Context, use clean IDs like 'char_lead_1', 'default_voice'. DO NOT use the MISSING_ASSET string.
        4. Generate new, original dialogue matching the new storyline in {language}.
        5. SHOT CONSOLIDATION & PACING: Consolidate into 3 to 5 continuous, cohesive scenes (3–8 seconds each) totaling approximately {target_dur}s.
        6. Ensure all scene actions, visual descriptions, and character actions are completely safe, family-friendly, and adhere to AI safety guidelines.
        """
        
        return self.synthesize_clone_blueprint(
            prompt=prompt, complexity=complexity, request=request,
            clone_blueprint=clone_blueprint, context=context,
        )

    def synthesize_clone_blueprint(self, prompt: str, complexity: str,
                                   request: ProductionTransformationRequest,
                                   clone_blueprint: CloneBlueprint,
                                   context: GenerationContext) -> ProductionBlueprint:
        """
        P3/Phase-B extraction: runs invoke -> parse -> bind lineage &
        preservation flags -> entity/originality validation -> cost estimate
        -> save(DRAFT v1) for an EXTERNALLY COMPILED prompt.

        - Legacy transform_clone_blueprint() delegates here unchanged, so its
          behavior is byte-identical (golden tests lock this).
        - UniversalCreativeDirector (Phase B) calls this directly, feeding
          TransformationContext.compile_prompt() output instead.
        Retry ladder and every exception semantic are preserved verbatim.
        """
        max_retries = 2
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    retry_prompt = prompt + f"\n\nYOUR PREVIOUS ATTEMPT FAILED WITH ERROR:\n{last_error}\nPlease fix the issues and ensure the story is completely new and original."
                else:
                    retry_prompt = prompt
                
                raw_json = self._invoke_story_model(retry_prompt, complexity=complexity)
                blueprint_data = _clean_and_parse_json(raw_json)
                blueprint = ProductionBlueprint(**blueprint_data)
                
                # Bind ownership, lineage, and preservation profile
                blueprint.project_id = self.project_id
                if not blueprint.blueprint_id:
                    blueprint.blueprint_id = f"pb_{uuid.uuid4().hex[:8]}"
                blueprint.source_clone_blueprint_id = clone_blueprint.clone_blueprint_id
                blueprint.source_clone_blueprint_version = clone_blueprint.clone_blueprint_version
                
                blueprint.clone_mode = request.clone_mode
                blueprint.preserve_visual_style = request.preserve_visual_style
                blueprint.preserve_characters = request.preserve_characters
                blueprint.preserve_environment = request.preserve_environment
                blueprint.preserve_camera_pacing = request.preserve_camera_pacing
                blueprint.preserve_trend_structure = request.preserve_trend_structure
                
                if request.preserve_visual_style:
                    blueprint.visual_style_profile = clone_blueprint.visual_style_profile
                    if clone_blueprint.visual_style_profile:
                        blueprint.authoritative_art_style = clone_blueprint.visual_style_profile.art_style
                else:
                    blueprint.authoritative_art_style = blueprint.concept
                
                if request.preserve_characters:
                    if clone_blueprint.visual_style_profile:
                        blueprint.authoritative_character_design = clone_blueprint.visual_style_profile.character_design
                else:
                    blueprint.authoritative_character_design = "Original characters created for story"
                
                # Validate entities (allow new characters/locations if not preserved)
                entity_errors = self._validate_entities(
                    blueprint, context, 
                    allow_new_chars=(not request.preserve_characters),
                    allow_new_locs=(not request.preserve_environment)
                )
                if entity_errors:
                    raise BlueprintValidationException("Entity validation failed.", errors=entity_errors)
                
                # Validate narrative originality & preservation compliance
                validate_blueprint_originality(
                    clone_blueprint, 
                    blueprint,
                    preserve_characters=request.preserve_characters,
                    preserve_environment=request.preserve_environment
                )
                
                self._estimate_costs(blueprint)
                
                blueprint.blueprint_version = 1
                blueprint.status = "DRAFT" # Draft by default until approved
                
                self.repo.save(self.user_id, blueprint)
                
                return blueprint
                
            except MissingAssetException:
                # Re-raise to abort immediately, do not retry missing assets
                raise
            except OriginalityValidationException as orig_err:
                last_error = str(orig_err)
                print(f"Originality Validation failed on attempt {attempt}: {last_error}")
            except (ValidationError, json.JSONDecodeError, ValueError) as pyd_err:
                last_error = str(pyd_err)
                print(f"Schema / JSON Validation failed on attempt {attempt}: {last_error}")
            except BlueprintValidationException as val_err:
                last_error = f"{val_err}: {val_err.errors}"
                print(f"Blueprint Entity Validation failed on attempt {attempt}: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"Unknown generation error on attempt {attempt}: {last_error}")
                
        raise Exception(f"Failed to transform CloneBlueprint after {max_retries} retries. Last error: {last_error}")
