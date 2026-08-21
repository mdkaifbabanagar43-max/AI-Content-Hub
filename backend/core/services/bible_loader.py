from typing import Optional, Dict, Any, List
from core.models.context import GenerationContext
from core.models.scene import Scene
from core.models.character import Character
from core.models.voice import Voice
from core.models.style import Style
from core.models.location import Location
from core.models.prop import Prop

from core.repositories.character_repo import CharacterRepository
from core.repositories.voice_repo import VoiceRepository
from core.repositories.style_repo import StyleRepository
from core.repositories.location_repo import LocationRepository
from core.repositories.prop_repo import PropRepository
from core.repositories.scene_repo import SceneRepository

class ResolvedScene:
    def __init__(
        self,
        scene: Scene,
        characters: List[Character],
        voices: List[Voice],
        style: Optional[Style],
        location: Optional[Location],
        props: List[Prop]
    ):
        self.scene = scene
        self.characters = characters
        self.voices = voices
        self.style = style
        self.location = location
        self.props = props

class ProjectBibleLoader:
    def __init__(self):
        self.char_repo = CharacterRepository()
        self.voice_repo = VoiceRepository()
        self.style_repo = StyleRepository()
        self.loc_repo = LocationRepository()
        self.prop_repo = PropRepository()
        self.scene_repo = SceneRepository()

    def load_all_bibles(self, context: GenerationContext) -> Dict[str, List[Any]]:
        return {
            "characters": self.char_repo.list(context.user_id, context.project_id),
            "voices": self.voice_repo.list(context.user_id, context.project_id),
            "styles": self.style_repo.list(context.user_id, context.project_id),
            "locations": self.loc_repo.list(context.user_id, context.project_id),
            "props": self.prop_repo.list(context.user_id, context.project_id),
        }

    def resolve_scene(self, context: GenerationContext, scene_id: str) -> ResolvedScene:
        """
        Loads a Scene and resolves all its ID references into canonical entities.
        Raises ValueError if a referenced entity is missing.
        """
        scene = self.scene_repo.get(context.user_id, context.project_id, scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found in project {context.project_id}")

        # Resolve Characters
        characters = []
        voices = []
        for char_id in scene.character_ids:
            char = self.char_repo.get(context.user_id, context.project_id, char_id)
            if not char:
                raise ValueError(f"Character {char_id} referenced in Scene {scene_id} not found.")
            characters.append(char)
            
            # Resolve Voice (optional, a character might not have a voice yet)
            # Find a voice that belongs to this character in this project
            # (In a real app, this might be a specific voice_id, but here Voice has character_id)
            # We can scan the voices for this character
            all_voices = self.voice_repo.list(context.user_id, context.project_id)
            char_voices = [v for v in all_voices if v.character_id == char.character_id]
            if char_voices:
                voices.append(char_voices[0])

        # Resolve Style
        style = None
        if scene.style_id:
            style = self.style_repo.get(context.user_id, context.project_id, scene.style_id)
            if not style:
                raise ValueError(f"Style {scene.style_id} referenced in Scene {scene_id} not found.")

        # Resolve Location
        location = None
        if scene.location_id:
            location = self.loc_repo.get(context.user_id, context.project_id, scene.location_id)
            if not location:
                raise ValueError(f"Location {scene.location_id} referenced in Scene {scene_id} not found.")

        # Resolve Props
        props = []
        for prop_id in scene.prop_ids:
            prop = self.prop_repo.get(context.user_id, context.project_id, prop_id)
            if not prop:
                raise ValueError(f"Prop {prop_id} referenced in Scene {scene_id} not found.")
            props.append(prop)

        return ResolvedScene(
            scene=scene,
            characters=characters,
            voices=voices,
            style=style,
            location=location,
            props=props
        )

    def resolve_scene_blueprint(self, context: GenerationContext, scene_blueprint: Any) -> ResolvedScene:
        """Resolves characters, voices, style, and props from a SceneBlueprint."""
        characters = []
        voices = []
        for char_id in getattr(scene_blueprint, "character_ids", []):
            char = self.char_repo.get(context.user_id, context.project_id, char_id)
            if char:
                characters.append(char)
                all_voices = self.voice_repo.list(context.user_id, context.project_id)
                char_voices = [v for v in all_voices if v.character_id == char.character_id]
                if char_voices:
                    voices.append(char_voices[0])

        style = None
        style_id = getattr(scene_blueprint, "style_id", None) or getattr(scene_blueprint, "visual_style_id", None)
        if style_id:
            style = self.style_repo.get(context.user_id, context.project_id, style_id)

        location = None
        location_id = getattr(scene_blueprint, "location_id", None)
        if location_id:
            location = self.loc_repo.get(context.user_id, context.project_id, location_id)

        props = []
        for prop_id in getattr(scene_blueprint, "prop_ids", []):
            prop = self.prop_repo.get(context.user_id, context.project_id, prop_id)
            if prop:
                props.append(prop)

        return ResolvedScene(
            scene=scene_blueprint,
            characters=characters,
            voices=voices,
            style=style,
            location=location,
            props=props
        )
