"""
Visual Identity Regression Test Suite
======================================
Tests for _sanitize_veo_prompt signature compatibility (default behavior,
is_animated=True, is_animated=False, positional callers, keyword callers)
and VisualIdentityPack construction.
"""
from unittest.mock import MagicMock, patch

from services.trend_remixer import _sanitize_veo_prompt
from core.services.visual_identity_service import VisualIdentityService


def test_sanitize_veo_prompt_default_behavior():
    """Test _sanitize_veo_prompt with only prompt argument (default kwargs)."""
    raw = "A cute padlock dancing in the room"
    sanitized = _sanitize_veo_prompt(raw)
    assert "9:16 vertical orientation" in sanitized
    assert "padlock dancing" in sanitized


def test_sanitize_veo_prompt_is_animated_true_explicit():
    """Test _sanitize_veo_prompt with explicit is_animated=True strips photorealistic tokens."""
    raw = "A real human actor character sheet, live action meme clip, photorealistic"
    sanitized = _sanitize_veo_prompt(raw, is_animated=True)
    assert "real human" not in sanitized.lower()
    assert "photorealistic" not in sanitized.lower()
    assert "live action" not in sanitized.lower()
    assert "9:16 vertical orientation" in sanitized


def test_sanitize_veo_prompt_is_animated_false_explicit():
    """Test _sanitize_veo_prompt with is_animated=False preserves photorealistic tokens."""
    raw = "A photorealistic human actor walking in the street"
    sanitized = _sanitize_veo_prompt(raw, is_animated=False)
    assert "photorealistic human actor" in sanitized
    assert "9:16 vertical orientation" in sanitized


def test_sanitize_veo_prompt_positional_three_args():
    """Test existing legacy positional 3-argument callers (prompt, art_style, character_design)."""
    raw = "dancing around in a room with live action elements"
    art_style = "3D Pixar-style digital animation"
    char_design = "A cute brass padlock character"
    sanitized = _sanitize_veo_prompt(raw, art_style, char_design)
    assert "live action" not in sanitized.lower()
    assert "3D Pixar-style" in sanitized
    assert "brass padlock" in sanitized
    assert "9:16 vertical orientation" in sanitized


def test_sanitize_veo_prompt_keyword_all_args():
    """Test keyword argument invocation with prompt, art_style, character_design, and is_animated."""
    raw = "Character sheet of Padlock, 3D animated character, live action clip"
    sanitized = _sanitize_veo_prompt(
        prompt=raw,
        art_style="3D animation",
        character_design="Padlock",
        is_animated=True
    )
    assert "live action" not in sanitized.lower()
    assert "3D animation" in sanitized
    assert "Padlock" in sanitized
    assert "9:16 vertical orientation" in sanitized


def test_sanitize_veo_prompt_non_animated_style_inferred():
    """Test that non-animated art style does not strip photorealistic tokens when is_animated=None."""
    raw = "Cinematic 8k shot of a real person reading a book"
    art_style = "Cinematic photorealism"
    char_design = "Middle-aged scholar"
    sanitized = _sanitize_veo_prompt(raw, art_style, char_design)
    assert "real person" in sanitized
    assert "9:16 vertical orientation" in sanitized


def test_visual_identity_pack_construction():
    """Test VisualIdentityService.build_or_get_visual_identity_pack with mocked image generation."""
    service = VisualIdentityService()
    service.vip_repo = MagicMock()
    service.vip_repo.get_latest.return_value = None
    service.char_repo = MagicMock()
    service.char_repo.get.return_value = None

    with patch("core.services.visual_identity_service.generate_character_reference", return_value="https://storage.googleapis.com/test-bucket/char_sheet.jpg"):
        pack = service.build_or_get_visual_identity_pack(
            user_id="user_test_123",
            project_id="proj_test_456",
            art_style="3D Pixar-style digital animation",
            character_design="3D animated characters",
            characters=["Padlock Guy"],
            environments=["Kitchen"],
            props=["Golden Key"]
        )

        assert pack is not None
        assert pack.project_id == "proj_test_456"
        assert len(pack.characters) == 1
        char_obj = list(pack.characters.values())[0]
        assert char_obj.name == "Padlock Guy"
        assert char_obj.master_sheet_uri == "https://storage.googleapis.com/test-bucket/char_sheet.jpg"
        assert len(pack.environments) == 1
        assert len(pack.props) == 1
        assert service.vip_repo.save.called
