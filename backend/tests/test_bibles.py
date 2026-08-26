from unittest.mock import MagicMock, patch

from core.models.character import Character, CharacterAppearance
from core.models.voice import Voice
from core.models.scene import Scene
from core.repositories.character_repo import CharacterRepository

def test_character_model_instantiation():
    """Verify Character creation and optional sub-models."""
    char = Character(
        character_id="CHAR_001",
        project_id="PROJ_123",
        name="Alex",
        appearance=CharacterAppearance(hair="Brown", eyes="Blue")
    )
    assert char.character_id == "CHAR_001"
    assert char.name == "Alex"
    assert char.appearance.hair == "Brown"
    assert char.body is None

def test_voice_model_instantiation():
    """Verify Voice model."""
    voice = Voice(
        voice_id="VOICE_001",
        character_id="CHAR_001",
        provider="elevenlabs",
        provider_voice_id="pNInz6obbf5AWCGqZrmY"
    )
    assert voice.provider == "elevenlabs"
    assert voice.provider_voice_id == "pNInz6obbf5AWCGqZrmY"
    assert voice.character_id == "CHAR_001"

def test_scene_model_relationships():
    """Verify Scene correctly references IDs rather than full objects."""
    scene = Scene(
        scene_id="SCENE_001",
        project_id="PROJ_123",
        scene_number=1,
        duration=5.0,
        character_ids=["CHAR_001"],
        location_id="LOC_001",
        style_id="STYLE_001",
        action="Walks into the room"
    )
    assert "CHAR_001" in scene.character_ids
    assert scene.location_id == "LOC_001"
    assert scene.style_id == "STYLE_001"

@patch('core.repositories.base_repo.get_db')
def test_legacy_character_fallback(mock_get_db):
    """Verify LegacyCharacterAdapter fallback logic."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    repo = CharacterRepository()
    
    # 1. Mock the specific document that will be returned
    mock_proj_doc = MagicMock()
    mock_proj_doc.exists = False
    
    # 2. Mock the character_refs collection returning legacy data
    mock_legacy_doc = MagicMock()
    mock_legacy_doc.exists = True
    mock_legacy_doc.to_dict.return_value = {
        "art_style": "3D Pixar",
        "character_design": "A cool dude",
        "veo_prefix": "3D Pixar, A cool dude, consistent",
        "canonical_reference_uri": "gs://bucket/ref.jpg"
    }
    
    def mock_collection(name):
        c = MagicMock()
        if name == "character_refs":
            c.document.return_value.get.return_value = mock_legacy_doc
        else:
            # db.collection("users").document(u).collection("projects").document(p).collection("characters").document(id).get()
            # We want the final .get() to return mock_proj_doc
            c.document.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_proj_doc
        return c
            
    mock_db.collection.side_effect = mock_collection
    
    # Test retrieving
    char = repo.get("USER_123", "PROJ_123", "LEGACY_001")
    
    assert char is not None
    assert char.character_id == "LEGACY_001"
    assert char.legacy_art_style == "3D Pixar"
    assert char.legacy_character_design == "A cool dude"
    assert char.canonical_reference_uri == "gs://bucket/ref.jpg"
    assert char.name == "LEGACY_001"  # Best effort name fallback
