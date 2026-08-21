"""
Character Reference System — Fix 2: Character Consistency

Stores and retrieves canonical character prompt seeds in Firestore so that
the same character set produces visually consistent Veo output across multiple
video generations.

Collection: character_refs/{character_set_id}
Document fields:
  - art_style:         str   (e.g. "3D Pixar-style animation")
  - character_design:  str   (e.g. "two toddlers in casual clothing")
  - veo_prefix:        str   (the full canonical Veo prompt prefix to prepend)
  - niche:             str
  - created_at:        datetime
  - usage_count:       int
"""

from datetime import datetime, timezone
from typing import Optional


def get_or_create_character_ref(
    character_set_id: str,
    art_style: str,
    character_design: str,
    niche: str = ""
) -> dict:
    """
    Retrieves a stored character reference from Firestore.
    If none exists for character_set_id, creates and stores one.

    Returns a dict with at minimum:
      {
        "character_set_id": str,
        "veo_prefix":       str,   # prepend this to every scene's veo_prompt
        "art_style":        str,
        "character_design": str,
      }
    """
    try:
        from core.firestore_client import get_db
        db = get_db()

        ref = db.collection("character_refs").document(character_set_id)
        doc = ref.get()

        if doc.exists:
            data = doc.to_dict()
            # Increment usage count (best-effort, non-blocking)
            try:
                ref.update({"usage_count": data.get("usage_count", 0) + 1})
            except Exception:
                pass
            print(f"[Character Refs] Loaded existing ref: {character_set_id}")
            return data

        # First time: build and store canonical reference
        veo_prefix = _build_veo_prefix(art_style, character_design)
        doc_data = {
            "character_set_id": character_set_id,
            "art_style": art_style,
            "character_design": character_design,
            "veo_prefix": veo_prefix,
            "niche": niche,
            "created_at": datetime.now(timezone.utc),
            "usage_count": 1
        }
        ref.set(doc_data)
        print(f"[Character Refs] Created new ref: {character_set_id} — prefix: {veo_prefix[:60]}...")
        return doc_data

    except Exception as e:
        print(f"[Character Refs] Firestore unavailable ({e}), using in-memory ref")
        veo_prefix = _build_veo_prefix(art_style, character_design)
        return {
            "character_set_id": character_set_id,
            "art_style": art_style,
            "character_design": character_design,
            "veo_prefix": veo_prefix,
            "niche": niche,
        }


def save_character_ref(character_set_id: str, data: dict) -> bool:
    """
    Upserts a character reference document in Firestore.
    Returns True on success, False on failure (non-blocking).
    """
    try:
        from core.firestore_client import get_db
        db = get_db()
        db.collection("character_refs").document(character_set_id).set(data, merge=True)
        return True
    except Exception as e:
        print(f"[Character Refs] Failed to save ref {character_set_id}: {e}")
        return False


def apply_character_seed(veo_prompt: str, character_ref: dict) -> str:
    """
    Prepends the canonical veo_prefix to a scene prompt if not already present.
    This is the main function called per-scene to enforce character consistency.

    Args:
        veo_prompt:     The scene-specific prompt from the AI Director.
        character_ref:  Dict returned by get_or_create_character_ref().

    Returns:
        The combined prompt with character seed prepended.
    """
    prefix = character_ref.get("veo_prefix", "")
    if not prefix:
        return veo_prompt

    # Avoid double-prepending if the prefix is already present
    if veo_prompt.lower().startswith(prefix.lower()[:30]):
        return veo_prompt

    return f"{prefix}, {veo_prompt}"


def _build_veo_prefix(art_style: str, character_design: str) -> str:
    """
    Builds a canonical prompt prefix from art style + character design.
    This seed is stored once and reused across all future Veo calls for this character set.
    """
    return f"{art_style}, {character_design}, consistent character appearance throughout"
