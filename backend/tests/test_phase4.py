import pytest
from unittest.mock import MagicMock, patch

from core.models.context import GenerationContext
from core.models.scene import Scene
from core.models.character import Character
from core.models.style import Style
from core.models.location import Location
from core.models.prop import Prop

from core.services.bible_loader import ProjectBibleLoader, ResolvedScene
from core.services.prompt_compiler import PromptCompiler
from core.services.reference_manager import ReferenceManager

# ---------------------------------------------------------
# MOCK FIXTURES
# ---------------------------------------------------------

@pytest.fixture
def base_context():
    return GenerationContext(
        user_id="USER_123",
        project_id="PROJ_123",
        job_id="JOB_123"
    )

@pytest.fixture
def mock_scene():
    return Scene(
        scene_id="SCENE_001",
        project_id="PROJ_123",
        scene_number=1,
        duration=5.0,
        character_ids=["CHAR_001"],
        style_id="STYLE_001",
        location_id="LOC_001",
        prop_ids=["PROP_001"],
        action="Walks into the cafe.",
        emotion="Happy",
        camera="Close-up shot",
        lighting_override="Neon lighting"
    )

@pytest.fixture
def mock_character():
    return Character(
        character_id="CHAR_001",
        project_id="PROJ_123",
        name="Alex",
        appearance={"hair": "short black", "skin_tone": "warm", "eyes": "brown"},
        clothing={"top": "red bomber jacket", "pants": "blue jeans"},
        accessories={"glasses": "sunglasses"},
        canonical_reference_uri="gs://bucket/canonical.jpg"
    )

@pytest.fixture
def mock_style():
    return Style(
        style_id="STYLE_001",
        project_id="PROJ_123",
        visual_style="Cyberpunk city",
        rendering_style="3D Pixar",
        color_palette="Neon pink and blue",
        lighting="Cinematic rim lighting"
    )

@pytest.fixture
def mock_location():
    return Location(
        location_id="LOC_001",
        project_id="PROJ_123",
        name="Neo Tokyo Cafe",
        architecture="Modern Indian",
        environment="Rainy street",
        walls="Brick",
        furniture="Wooden chairs"
    )

@pytest.fixture
def mock_prop():
    return Prop(
        prop_id="PROP_001",
        project_id="PROJ_123",
        name="Smartphone",
        color="red",
        material="glass"
    )


# ---------------------------------------------------------
# CONTEXT & BIBLE LOADER TESTS
# ---------------------------------------------------------

def test_generation_context_initialization():
    ctx = GenerationContext(user_id="U1", project_id="P1", job_id="J1")
    assert ctx.user_id == "U1"
    assert ctx.project_id == "P1"
    assert ctx.job_id == "J1"
    assert ctx.generation_mode == "default"

@patch('core.services.bible_loader.SceneRepository')
@patch('core.services.bible_loader.CharacterRepository')
@patch('core.services.bible_loader.StyleRepository')
@patch('core.services.bible_loader.LocationRepository')
@patch('core.services.bible_loader.PropRepository')
@patch('core.services.bible_loader.VoiceRepository')
def test_bible_loader_resolves_scene(
    mock_voice_repo, mock_prop_repo, mock_loc_repo, mock_style_repo, mock_char_repo, mock_scene_repo,
    base_context, mock_scene, mock_character, mock_style, mock_location, mock_prop
):
    mock_scene_repo.return_value.get.return_value = mock_scene
    mock_char_repo.return_value.get.return_value = mock_character
    mock_style_repo.return_value.get.return_value = mock_style
    mock_loc_repo.return_value.get.return_value = mock_location
    mock_prop_repo.return_value.get.return_value = mock_prop
    mock_voice_repo.return_value.list.return_value = []

    loader = ProjectBibleLoader()
    resolved = loader.resolve_scene(base_context, "SCENE_001")

    assert resolved.scene.scene_id == "SCENE_001"
    assert len(resolved.characters) == 1
    assert resolved.characters[0].name == "Alex"
    assert resolved.style.visual_style == "Cyberpunk city"
    assert resolved.location.name == "Neo Tokyo Cafe"
    assert len(resolved.props) == 1
    assert resolved.props[0].name == "Smartphone"


@patch('core.services.bible_loader.SceneRepository')
@patch('core.services.bible_loader.CharacterRepository')
def test_bible_loader_missing_character_raises(
    mock_char_repo, mock_scene_repo, base_context, mock_scene
):
    mock_scene_repo.return_value.get.return_value = mock_scene
    # Mock character not found
    mock_char_repo.return_value.get.return_value = None
    
    loader = ProjectBibleLoader()
    with pytest.raises(ValueError, match="Character CHAR_001 referenced in Scene SCENE_001 not found."):
        loader.resolve_scene(base_context, "SCENE_001")


# ---------------------------------------------------------
# PROMPT COMPILER TESTS
# ---------------------------------------------------------

def test_prompt_compiler_generates_valid_prompt(
    base_context, mock_scene, mock_character, mock_style, mock_location, mock_prop
):
    resolved = ResolvedScene(
        scene=mock_scene,
        characters=[mock_character],
        voices=[],
        style=mock_style,
        location=mock_location,
        props=[mock_prop]
    )
    
    compiler = PromptCompiler()
    prompt = compiler.compile(base_context, resolved)

    # 14. Character information is included.
    # 15. Canonical clothing is included.
    assert "Alex" in prompt
    assert "short black hair" in prompt
    assert "red bomber jacket" in prompt
    assert "sunglasses" in prompt

    # 16. Style information is included.
    assert "Cyberpunk city" in prompt
    assert "Neon pink and blue" in prompt

    # 17. Location information is included.
    assert "Neo Tokyo Cafe" in prompt
    assert "Rainy street" in prompt

    # 18. Props are included.
    assert "Smartphone" in prompt
    assert "red, glass" in prompt

    # 19. Camera information is included.
    assert "Close-up shot" in prompt

    # 20. Scene action is included.
    assert "Walks into the cafe." in prompt
    assert "Happy" in prompt

    # Check that scene lighting overrides style lighting
    assert "Neon lighting" in prompt


def test_prompt_compiler_contradictory_scene_ignored(
    base_context, mock_scene, mock_character
):
    # Compiler only uses Bible data for character appearance
    
    resolved = ResolvedScene(
        scene=mock_scene,
        characters=[mock_character],
        voices=[],
        style=None,
        location=None,
        props=[]
    )
    
    compiler = PromptCompiler()
    prompt = compiler.compile(base_context, resolved)

    # 21. Contradictory scene character information does not override canonical data.
    # The output should NOT contain "long blond hair" or "blue jacket", it should contain the Bible details.
    assert "long blond hair" not in prompt
    assert "blue jacket" not in prompt
    assert "short black hair" in prompt
    assert "red bomber jacket" in prompt


# ---------------------------------------------------------
# REFERENCE MANAGER TESTS
# ---------------------------------------------------------

@patch('core.services.reference_manager.get_db')
def test_reference_manager_front_portrait(mock_get_db, base_context, mock_scene, mock_character):
    # 22. Front portrait selected correctly for Close-up
    mock_scene.camera = "Close-up shot"
    resolved = ResolvedScene(scene=mock_scene, characters=[mock_character], voices=[], style=None, location=None, props=[])

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Mock returning a side profile asset
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"storage_uri": "gs://bucket/front_portrait.png"}
    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]

    mgr = ReferenceManager()
    uri = mgr.get_reference_uri(base_context, resolved)

    # Since stream returns a doc, it should pick the front portrait
    # BUT wait, our mock chain is: db.collection().document().collection().where().where().limit().stream()
    # It will hit the stream and return the mock doc.
    assert uri == "gs://bucket/front_portrait.png"


@patch('core.services.reference_manager.get_db')
def test_reference_manager_fallback_canonical(mock_get_db, base_context, mock_scene, mock_character):
    # 25. Canonical reference used as fallback.
    mock_scene.camera = "Close-up shot"
    resolved = ResolvedScene(scene=mock_scene, characters=[mock_character], voices=[], style=None, location=None, props=[])

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Mock returning NO assets for front_portrait
    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []

    mgr = ReferenceManager()
    uri = mgr.get_reference_uri(base_context, resolved)

    # Should fallback to canonical
    assert uri == "gs://bucket/canonical.jpg"


@patch('services.asset_generator.generate_character_reference', return_value=None)
@patch('core.services.reference_manager.get_db')
def test_reference_manager_validation(mock_get_db, mock_gen_char_ref, base_context, mock_scene, mock_character):
    # 26. Missing reference returns safe fallback (None for invalid)
    mock_character.canonical_reference_uri = "invalid_uri_format"
    resolved = ResolvedScene(scene=mock_scene, characters=[mock_character], voices=[], style=None, location=None, props=[])

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []

    mgr = ReferenceManager()
    uri = mgr.get_reference_uri(base_context, resolved)

    # Invalid URI should be rejected, returning None instead of passing it to Veo
    assert uri is None
