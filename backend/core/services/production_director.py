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

    def _validate_entities(self, blueprint: ProductionBlueprint, context: GenerationContext) -> List[str]:
        """
        Server-side independent validation of all Bible IDs and project scoping.
        Never trusts the LLM.
        """
        errors = []
        bibles = self.bible_loader.load_all_bibles(context)
        valid_chars = {b.character_id for b in bibles.get("characters", [])}
        valid_locs = {b.location_id for b in bibles.get("locations", [])}
        valid_props = {b.prop_id for b in bibles.get("props", [])}
        valid_voices = {b.voice_id for b in bibles.get("voices", [])} | {"default_voice", "default", "voice_default", "none", None}
        valid_styles = {b.style_id for b in bibles.get("styles", [])}
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
            if c_id not in valid_chars:
                errors.append(f"Missing character: {c_id}")
        for l_id in blueprint.required_location_ids:
            _check_missing_asset(l_id)
            if l_id not in valid_locs:
                errors.append(f"Missing location: {l_id}")
        for p_id in blueprint.required_prop_ids:
            _check_missing_asset(p_id)
            if p_id not in valid_props:
                errors.append(f"Missing prop: {p_id}")
                
        if blueprint.visual_style_id:
            _check_missing_asset(blueprint.visual_style_id)
            if blueprint.visual_style_id not in valid_styles:
                errors.append(f"Missing style: {blueprint.visual_style_id}")
            
        if blueprint.audio_strategy and blueprint.audio_strategy.primary_voice_id:
            if blueprint.audio_strategy.primary_voice_id not in valid_voices:
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
                if c_id not in valid_chars:
                    errors.append(f"Scene {s.scene_id} character missing: {c_id}")
                    
            if s.location_id:
                _check_missing_asset(s.location_id, s.scene_id)
                if s.location_id not in valid_locs:
                    errors.append(f"Scene {s.scene_id} location missing: {s.location_id}")
                
            for p_id in s.prop_ids:
                _check_missing_asset(p_id, s.scene_id)
                if p_id not in valid_props:
                    errors.append(f"Scene {s.scene_id} prop missing: {p_id}")
                    
            if s.primary_reference_asset_id:
                _check_missing_asset(s.primary_reference_asset_id, s.scene_id)
                if s.primary_reference_asset_id not in all_valid_entity_ids:
                    errors.append(f"Scene {s.scene_id} primary reference asset missing: {s.primary_reference_asset_id}")
                
            for req in s.continuity_requirements:
                if req.asset_id not in all_valid_entity_ids:
                    errors.append(f"Scene {s.scene_id} continuity asset missing: {req.asset_id}")
            
            for d in s.dialogue:
                if d.character_id not in valid_chars:
                    errors.append(f"Dialogue character missing: {d.character_id}")
                if d.voice_id not in valid_voices:
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
        
        prompt = f"""
        You are an AI Production Director transforming a SOURCE STRUCTURAL BLUEPRINT into a NEW ORIGINAL PRODUCTION.
        
        USER TRANSFORMATION REQUEST:
        - Topic: {request.topic}
        - Story Change: {request.story_change}
        - Target Duration: {request.target_duration_seconds}s
        - Tone: {request.tone}
        - Language: {request.language}
        
        REQUESTED ASSETS (You must use these if provided, or select appropriately from Project Context):
        - Style: {request.requested_style_id}
        - Characters: {request.requested_character_ids}
        - Voices: {request.requested_voice_id}
        - Locations: {request.requested_location_ids}
        - Props: {request.requested_prop_ids}
        
        PRESERVATION FLAGS:
        - Preserve Structure: {request.preserve_structure}
        - Preserve Pacing: {request.preserve_pacing}
        - Preserve Camera Language: {request.preserve_camera_language}
        - Preserve Emotional Arc: {request.preserve_emotional_arc}
        
        {planning_context}
        
        SOURCE BLUEPRINT STRUCTURE:
        {clone_blueprint.model_dump_json(indent=2)}
        
        INSTRUCTIONS:
        1. Preserve the narrative function, pacing profile, emotional progression, and camera language of the source blueprint.
        2. Transform the story details, dialogue, characters, locations, and props to match the User Transformation Request.
        3. You MUST use ONLY the supplied Project Bible IDs for characters, locations, props, voices, and styles. NEVER invent standard entity IDs like CHAR_999.
        4. If a required asset (style, character, etc.) from the Source Blueprint is missing from the Project Context, YOU MUST CHOOSE THE CLOSEST MATCHING ASSET from the Project Context. If there are no assets of that type available in the Project Context at all, you MUST omit the field (set to null or empty list). DO NOT use the MISSING_ASSET string.
        5. Generate new dialogue matching the narrative purpose and approximate timing.
        6. Adjust shot durations proportionally if the Target Duration differs from the Source Duration. Do not exceed the target duration.
        7. Ensure all scene actions, visual descriptions, and character actions are completely safe, family-friendly, and adhere to AI safety guidelines (avoiding any sensitive terms, violence, or dangerous actions that could trigger video generation safety filters).
        8. SHOT CONSOLIDATION & CONTINUITY: Consolidate short, fragmented micro-beats (< 3 seconds) occurring in the same setting into cohesive, continuous narrative scenes (4–8 seconds each). Aim for 3 to 6 rich, continuous scenes rather than dozens of 1-second cuts. This preserves character presence, room lighting, and narrative immersion while keeping video generation fast and unified.
        9. LOCATION CONTINUITY: Unless the user explicitly requests a location change, preserve the source visual world setting as described in the Source Blueprint. Do NOT arbitrarily invent unrelated locations that differ from the source video's environment.
        10. CHARACTER IDENTITY AS HARD CONSTRAINT: Preserve the physical visual identity of the characters exactly as described in the Source Blueprint's visual style and character design fields across all scenes. Do NOT alter their species, form factor, or visual aesthetic unless the user explicitly requests it.
        """
        
        max_retries = 2
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    retry_prompt = prompt + f"\n\nYOUR PREVIOUS ATTEMPT FAILED WITH ERROR:\n{last_error}\nPlease fix the issues and try again."
                else:
                    retry_prompt = prompt
                
                raw_json = self._invoke_story_model(retry_prompt, complexity=complexity)
                blueprint_data = _clean_and_parse_json(raw_json)
                blueprint = ProductionBlueprint(**blueprint_data)
                
                # Bind ownership and lineage
                blueprint.project_id = self.project_id
                if not blueprint.blueprint_id:
                    blueprint.blueprint_id = f"pb_{uuid.uuid4().hex[:8]}"
                blueprint.source_clone_blueprint_id = clone_blueprint.clone_blueprint_id
                blueprint.source_clone_blueprint_version = clone_blueprint.clone_blueprint_version
                blueprint.visual_style_profile = clone_blueprint.visual_style_profile
                if clone_blueprint.visual_style_profile:
                    blueprint.authoritative_art_style = clone_blueprint.visual_style_profile.art_style
                    blueprint.authoritative_character_design = clone_blueprint.visual_style_profile.character_design
                
                # Validate
                entity_errors = self._validate_entities(blueprint, context)
                if entity_errors:
                    raise BlueprintValidationException("Entity validation failed.", errors=entity_errors)
                
                self._estimate_costs(blueprint)
                
                blueprint.blueprint_version = 1
                blueprint.status = "DRAFT" # Draft by default until approved
                
                self.repo.save(self.user_id, blueprint)
                
                return blueprint
                
            except MissingAssetException:
                # Re-raise to abort immediately, do not retry missing assets
                raise
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
