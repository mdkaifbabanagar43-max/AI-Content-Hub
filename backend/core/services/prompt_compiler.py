from typing import Optional, Any
from core.models.context import GenerationContext
from core.services.bible_loader import ResolvedScene
from core.models.state import SceneState

def normalize_enum_val(val: Any, default: str = "") -> str:
    """Safely normalizes enums, strings, and other types to clean string values."""
    if val is None:
        return default
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)

class PromptCompiler:
    def compile(self, context: GenerationContext, resolved_scene: ResolvedScene, previous_state: Optional[SceneState] = None, scene_blueprint=None) -> str:
        """
        Converts structured project data into a model-ready Veo prompt.
        Prioritizes Canonical Bible data over individual scene variations.
        Accepts optional `scene_blueprint` of type SceneBlueprint.
        """
        scene = resolved_scene.scene
        parts = []

        # 1. SUBJECT / CHARACTERS & 2. CHARACTER APPEARANCE & 3. CLOTHING & 4. ACCESSORIES
        if resolved_scene.characters:
            char_desc = []
            for char in resolved_scene.characters:
                desc = f"Character '{char.name}':"
                
                # Appearance (Bible priority)
                if char.appearance:
                    app = []
                    if char.appearance.face_shape: app.append(normalize_enum_val(char.appearance.face_shape))
                    if char.appearance.skin_tone: app.append(f"{normalize_enum_val(char.appearance.skin_tone)} skin")
                    if char.appearance.hair: app.append(f"{normalize_enum_val(char.appearance.hair)} hair")
                    if char.appearance.eyes: app.append(f"{normalize_enum_val(char.appearance.eyes)} eyes")
                    if char.appearance.facial_features: app.append(normalize_enum_val(char.appearance.facial_features))
                    if app:
                        desc += f" Appearance: {', '.join(app)}."
                
                # Legacy fallback
                if not char.appearance and char.legacy_character_design:
                    desc += f" Appearance: {char.legacy_character_design}."

                # Clothing
                if char.clothing:
                    cloth = []
                    if char.clothing.top: cloth.append(normalize_enum_val(char.clothing.top))
                    if char.clothing.inner_clothing: cloth.append(normalize_enum_val(char.clothing.inner_clothing))
                    if char.clothing.pants: cloth.append(normalize_enum_val(char.clothing.pants))
                    if char.clothing.shoes: cloth.append(normalize_enum_val(char.clothing.shoes))
                    if cloth:
                        desc += f" Wearing: {', '.join(cloth)}."
                        
                # Accessories
                if char.accessories:
                    acc = []
                    if char.accessories.glasses: acc.append(normalize_enum_val(char.accessories.glasses))
                    if char.accessories.watch: acc.append(normalize_enum_val(char.accessories.watch))
                    if char.accessories.backpack: acc.append(normalize_enum_val(char.accessories.backpack))
                    if acc:
                        desc += f" Accessories: {', '.join(acc)}."

                char_desc.append(desc)
            
            parts.append("SUBJECTS:\n" + "\n".join(char_desc))

        # 5. LOCATION
        if resolved_scene.location:
            loc = resolved_scene.location
            loc_parts = []
            if loc.architecture: loc_parts.append(normalize_enum_val(loc.architecture))
            if loc.environment: loc_parts.append(normalize_enum_val(loc.environment))
            if loc.walls: loc_parts.append(f"Walls: {normalize_enum_val(loc.walls)}")
            if loc.furniture: loc_parts.append(f"Furniture: {normalize_enum_val(loc.furniture)}")
            if loc.signature_elements: loc_parts.append(normalize_enum_val(loc.signature_elements))
            parts.append(f"LOCATION:\n{loc.name}. " + ", ".join(loc_parts))
            
        # 6. PROPS
        if resolved_scene.props:
            prop_lines = []
            for p in resolved_scene.props:
                desc = p.name
                details = [normalize_enum_val(x) for x in [p.color, p.material, p.shape, p.defining_details] if x]
                if details:
                    desc += f" ({', '.join(details)})"
                prop_lines.append(desc)
            parts.append(f"PROPS:\n" + ", ".join(prop_lines))

        # 7. ACTION & 8. EMOTION
        action_parts = []
        
        # Merge action from blueprint and scene
        action_val = (scene_blueprint.action if scene_blueprint else None) or (getattr(scene, 'action', None))
        if action_val:
            action_parts.append(f"Action: {normalize_enum_val(action_val)}")
            
        emotion_val = (scene_blueprint.emotion if scene_blueprint else None) or (getattr(scene, 'emotion', None))
        if emotion_val:
            action_parts.append(f"Emotion: {normalize_enum_val(emotion_val)}")
        
        if action_parts:
            parts.append("SCENE DYNAMICS:\n" + "\n".join(action_parts))

        # 9. CAMERA & 10. LIGHTING
        cam_light = []
        if scene_blueprint and scene_blueprint.camera:
            cam = scene_blueprint.camera
            cam_str = []
            shot_type = normalize_enum_val(cam.shot_type)
            if shot_type: cam_str.append(f"{shot_type} SHOT")
            lens = normalize_enum_val(cam.lens)
            if lens: cam_str.append(f"{lens} lens")
            camera_motion = normalize_enum_val(cam.camera_motion)
            if camera_motion: cam_str.append(f"{camera_motion} camera motion")
            angle = normalize_enum_val(cam.angle)
            if angle: cam_str.append(f"{angle} angle")
            framing = normalize_enum_val(cam.framing)
            if framing: cam_str.append(f"{framing} framing")
            depth_of_field = normalize_enum_val(cam.depth_of_field)
            if depth_of_field: cam_str.append(f"{depth_of_field} depth of field")
            if cam_str:
                cam_light.append("Camera: " + ", ".join(cam_str) + ".")
        elif getattr(scene, 'camera', None):
            cam_light.append(f"Camera: {normalize_enum_val(scene.camera)}")
            
        # Lighting overrides style lighting if present
        lighting = None
        if scene_blueprint and scene_blueprint.camera and scene_blueprint.camera.lighting:
            lighting = normalize_enum_val(scene_blueprint.camera.lighting)
        elif getattr(scene, 'lighting_override', None):
            lighting = normalize_enum_val(scene.lighting_override)
        elif resolved_scene.style and resolved_scene.style.lighting:
            lighting = normalize_enum_val(resolved_scene.style.lighting)
            
        if lighting:
            cam_light.append(f"Lighting: {lighting}")
        
        env = normalize_enum_val(scene_blueprint.environment) if scene_blueprint else None
        if env:
            cam_light.append(f"Environment/Vibe: {env}")
            
        if cam_light:
            parts.append("CINEMATOGRAPHY:\n" + "\n".join(cam_light))

        # 11. VISUAL STYLE
        if resolved_scene.style:
            s = resolved_scene.style
            s_parts = []
            if s.visual_style: s_parts.append(s.visual_style)
            if s.rendering_style: s_parts.append(s.rendering_style)
            if s.color_palette: s_parts.append(f"Palette: {s.color_palette}")
            if s.film_grain: s_parts.append(f"Grain: {s.film_grain}")
            if s.lens_language: s_parts.append(f"Lens: {s.lens_language}")
            parts.append("VISUAL STYLE:\n" + ", ".join(s_parts))
            
        # Legacy style fallback
        elif resolved_scene.characters and resolved_scene.characters[0].legacy_art_style:
            parts.append(f"VISUAL STYLE:\n{resolved_scene.characters[0].legacy_art_style}")

        # 12. CONTINUITY INSTRUCTIONS
        continuity_parts = []
        
        # From Blueprint (Desired future state)
        if scene_blueprint and scene_blueprint.continuity_requirements:
            for req in scene_blueprint.continuity_requirements:
                continuity_parts.append(f"REQUIRED: {req.required_state} (Priority: {req.priority})")
        
        # From Bible (Static notes)
        if getattr(scene, 'continuity_notes', None):
            continuity_parts.append(scene.continuity_notes)
            
        if previous_state:
            state_notes = []
            for c in previous_state.character_states:
                # Find character name
                char_name = c.character_id
                for rc in resolved_scene.characters:
                    if rc.character_id == c.character_id:
                        char_name = rc.name
                        break
                        
                if c.clothing_state:
                    state_notes.append(f"{char_name} is wearing {c.clothing_state}.")
                if c.held_objects:
                    state_notes.append(f"{char_name} was holding: {', '.join(c.held_objects)}.")
                if c.emotional_state:
                    state_notes.append(f"{char_name} was {c.emotional_state}.")
                    
            if previous_state.environment_state and previous_state.environment_state.lighting_state:
                state_notes.append(f"Lighting was {previous_state.environment_state.lighting_state}.")
                
            if state_notes:
                continuity_parts.append("\n".join(state_notes))
                continuity_parts.append("Maintain the same character identity and environment. Continue naturally from the previous action.")
                
        if continuity_parts:
            parts.append("CONTINUITY FROM PREVIOUS SCENE:\n" + "\n\n".join(continuity_parts))

        compiled_raw = "\n\n".join(parts)
        
        # Apply token sanitization for animated styles
        try:
            import re
            from services.trend_remixer import _PHOTOREALISTIC_TOKENS, _is_animated_style
            art_style_str = normalize_enum_val(getattr(context, "metadata", {}).get("art_style", "") if context and context.metadata else "")
            if _is_animated_style(art_style_str):
                for token_pattern in _PHOTOREALISTIC_TOKENS:
                    compiled_raw = re.sub(token_pattern, "", compiled_raw, flags=re.IGNORECASE)
                compiled_raw = re.sub(r"  +", " ", compiled_raw).strip()
        except Exception:
            pass

        return compiled_raw
