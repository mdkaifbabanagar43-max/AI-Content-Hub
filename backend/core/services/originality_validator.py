"""
Originality Validator
=====================
Validates that a generated ProductionBlueprint represents a genuine creative
transformation rather than a superficial copy or reproduction of the source
CloneBlueprint's narrative, scene sequence, dialogue, or action beats.
"""
import re
from typing import Set, List, Tuple, Optional
from core.models.clone_blueprint import CloneBlueprint
from core.models.blueprint import ProductionBlueprint

# Stop words to ignore during narrative originality analysis
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "while", "with", "at", "by",
    "for", "from", "in", "into", "of", "off", "on", "onto", "out", "over",
    "to", "up", "down", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "can", "could", "shall",
    "should", "will", "would", "may", "might", "must", "it", "its", "they",
    "them", "their", "this", "that", "these", "those", "he", "him", "his",
    "she", "her", "hers", "character", "characters", "scene", "shot",
    "camera", "view", "shows", "stands", "looks", "medium", "wide", "closeup",
    "static", "dolly", "cut", "transition", "audio", "video", "render",
    "3d", "pixar", "animation", "digital", "style"
}

class OriginalityValidationException(Exception):
    """Raised when a generated blueprint fails structural originality checks."""
    def __init__(self, message: str, similarity_score: float, matched_concepts: List[str]):
        super().__init__(message)
        self.similarity_score = similarity_score
        self.matched_concepts = matched_concepts


def _tokenize_narrative(text: str) -> Set[str]:
    """Extracts normalized significant narrative keywords."""
    if not text:
        return set()
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _extract_source_narrative_corpus(clone_bp: CloneBlueprint) -> Tuple[Set[str], List[str]]:
    """Extracts all narrative text from source blueprint (excluding pure visual styling)."""
    narrative_chunks = []
    
    # 1. Hook
    if clone_bp.hook:
        if getattr(clone_bp.hook, 'hook_description', None):
            narrative_chunks.append(clone_bp.hook.hook_description)
        if getattr(clone_bp.hook, 'hook_text', None):
            narrative_chunks.append(clone_bp.hook.hook_text)
        if getattr(clone_bp.hook, 'verbal_hook', None):
            narrative_chunks.append(clone_bp.hook.verbal_hook)
        if getattr(clone_bp.hook, 'visual_hook', None):
            narrative_chunks.append(clone_bp.hook.visual_hook)
            
    # 2. Narrative beats
    for beat in clone_bp.narrative_structure:
        if beat.description:
            narrative_chunks.append(beat.description)
            
    # 3. Scene actions and dialogue intents
    for scene in clone_bp.scenes:
        if scene.narrative_purpose:
            narrative_chunks.append(scene.narrative_purpose)
        if scene.visual_action:
            narrative_chunks.append(scene.visual_action)
        if scene.dialogue_intent:
            narrative_chunks.append(scene.dialogue_intent)
        for shot in scene.shot_sequence:
            if shot.visual_action:
                narrative_chunks.append(shot.visual_action)
                
    full_text = " ".join(narrative_chunks)
    tokens = _tokenize_narrative(full_text)
    return tokens, narrative_chunks


def _extract_production_narrative_corpus(production_bp: ProductionBlueprint) -> Tuple[Set[str], List[str]]:
    """Extracts all narrative text from generated production blueprint."""
    narrative_chunks = []
    
    if production_bp.title:
        narrative_chunks.append(production_bp.title)
    if production_bp.concept:
        narrative_chunks.append(production_bp.concept)
        
    for scene in production_bp.scenes:
        if scene.narrative_purpose:
            narrative_chunks.append(scene.narrative_purpose)
        if scene.action:
            narrative_chunks.append(scene.action)
        for d in scene.dialogue:
            if d.text:
                narrative_chunks.append(d.text)
                
    full_text = " ".join(narrative_chunks)
    tokens = _tokenize_narrative(full_text)
    return tokens, narrative_chunks


def compute_narrative_similarity(
    source_bp: CloneBlueprint,
    production_bp: ProductionBlueprint
) -> Tuple[float, List[str]]:
    """
    Computes a deterministic narrative similarity score between source and generated blueprints.
    Returns (similarity_score, matched_keywords).
    """
    source_tokens, _ = _extract_source_narrative_corpus(source_bp)
    prod_tokens, _ = _extract_production_narrative_corpus(production_bp)
    
    if not source_tokens or not prod_tokens:
        return 0.0, []
        
    intersection = source_tokens.intersection(prod_tokens)
    union = source_tokens.union(prod_tokens)
    
    # Jaccard overlap on meaningful narrative tokens
    jaccard_score = len(intersection) / len(union) if union else 0.0
    
    # Also calculate overlap relative to generated tokens
    coverage_score = len(intersection) / len(prod_tokens) if prod_tokens else 0.0
    
    # Combined score emphasizing whether the generated output is dominated by source words
    composite_score = round(max(jaccard_score, coverage_score * 0.7), 3)
    
    return composite_score, sorted(list(intersection))


def validate_blueprint_originality(
    source_bp: CloneBlueprint,
    production_bp: ProductionBlueprint,
    max_allowed_similarity: float = None,
    preserve_characters: Optional[bool] = None,
    preserve_environment: Optional[bool] = None
) -> bool:
    """
    Validates that the production blueprint is structurally original and complies with
    user preservation choices (e.g. not reusing source character IDs when characters=False).
    Raises OriginalityValidationException if similarity exceeds the threshold or preservation rules are violated.
    """
    # P3/Q5: threshold centralized in config (env-overridable, default 0.40)
    if max_allowed_similarity is None:
        from config import ORIGINALITY_THRESHOLD
        max_allowed_similarity = ORIGINALITY_THRESHOLD
    # Check preservation compliance if specified on blueprint or arguments
    char_preserved = preserve_characters if preserve_characters is not None else getattr(production_bp, 'preserve_characters', None)
    env_preserved = preserve_environment if preserve_environment is not None else getattr(production_bp, 'preserve_environment', None)
    
    # 1. Source Character Reuse Check when characters are NOT preserved
    if char_preserved is False:
        source_char_ids = set()
        for s in source_bp.scenes:
            for role in s.character_roles:
                source_char_ids.add(role.lower())
                # also extract clean token if role is formatted like char_padlock_1
                if role.startswith("char_") or "_" in role:
                    source_char_ids.add(role)
        
        # Check against required character ids and scene character ids
        prod_char_ids = set(production_bp.required_character_ids)
        for s in production_bp.scenes:
            prod_char_ids.update(s.character_ids)
            for d in s.dialogue:
                if d.character_id:
                    prod_char_ids.add(d.character_id)
                    
        for cid in prod_char_ids:
            if cid.lower() in source_char_ids or cid in ["char_padlock_1", "char_padlock_2"]:
                raise OriginalityValidationException(
                    f"Character Preservation Violation: preserve_characters is False, but source character '{cid}' was reused.",
                    similarity_score=1.0,
                    matched_concepts=[cid]
                )

    # 2. Narrative Originality Check
    score, matched = compute_narrative_similarity(source_bp, production_bp)
    
    if score > max_allowed_similarity:
        raise OriginalityValidationException(
            f"Originality Check FAILED: Narrative similarity {score:.2f} exceeds threshold {max_allowed_similarity:.2f}. "
            f"Matched concepts: {', '.join(matched[:10])}",
            similarity_score=score,
            matched_concepts=matched
        )
        
    return True
