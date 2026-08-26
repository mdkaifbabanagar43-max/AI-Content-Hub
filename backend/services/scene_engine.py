
import re
import json
import traceback
from typing import List, Dict
import re
import json
import traceback
from typing import List, Dict
from services.ai_service import generate_text

class SceneEngine:
    def __init__(self):
        pass

    def analyze_script(self, script_text: str) -> List[Dict]:
        """
        Analyzes script for EMOTION-DRIVEN visual matching.
        Chunks by emotional/energy shifts, not sentences.
        """
        print(f"[SceneEngine] Emotion-Driven Analysis ({len(script_text)} chars)...")
        
        prompt = f"""
        You are an expert SHORT-FORM Video Director who matches VISUALS TO EMOTION, not literal words.
        
        CORE PRINCIPLE:
        Audio leads. Visuals reinforce emotion and intent.
        NEVER match visuals word-for-word with audio text.
        
        TASK:
        Split this script into EMOTIONAL CHUNKS and generate Pexels queries that match the FEELING.
        
        SCRIPT:
        "{script_text}"
        
        STEP 1 - EMOTIONAL CHUNKING:
        - Split script when EMOTION or ENERGY changes
        - NOT strictly sentence-based
        - Each chunk: 15-20 words MAX (to enforce fast, dynamic pacing)
        - Each chunk: ~2.5 seconds of spoken audio
        
        STEP 2 - EXTRACT FOR EACH CHUNK:
        - Core meaning (what's being communicated)
        - Emotion: struggle / focus / hope / confidence / calm / urgency / curiosity
        - Energy: low / medium / high
        
        STEP 3 - VISUAL SELECTION (PRIORITY ORDER):
        1. EMOTION MATCH (most important)
        2. ENERGY MATCH (second priority)
        3. CONTEXT MATCH (last priority)
        
        VISUAL RULES:
        ✅ PREFER: Human faces, natural movement, medium/close shots
        ❌ AVOID: Abstract visuals, distracting motion, literal object matches
        
        QUERY FORMAT: [Person Type] + [Emotion Expression] + [Natural Action]
        - ✅ GOOD: "thoughtful person looking away", "excited woman celebration", "calm man breathing deep"
        - ❌ BAD: "laptop", "money", "success", "business graph"
        
        CLIP DURATION STRATEGY:
        - If consecutive chunks have SAME emotion+energy, mark "merge_with_previous": true
        - This allows one clip to span multiple audio chunks for natural flow, but try to keep it under 4 seconds total.
        
        FALLBACK if no perfect match:
        - "person walking fast", "dynamic human movement", "focused face closeup"
        - NEVER use random B-roll or abstract footage. Always use human-centric high-motion keywords.
        
        OUTPUT FORMAT (JSON ARRAY ONLY):
        [
            {{
                "text": "The chunk of text from script",
                "emotion": "specific emotion (struggle/focus/hope/confidence/calm/urgency/curiosity)",
                "energy": "low/medium/high",
                "keywords": ["emotion-matched query 1", "backup query 2", "neutral fallback 3"],
                "merge_with_previous": false,
                "reasoning": "Brief explanation of why this visual matches the emotion"
            }},
            ...
        ]
        """
        
        try:
            response_text = generate_text(prompt, temperature=0.3)
            
            # Clean and parse
            text_resp = response_text.strip()
            if text_resp.startswith("```"):
                text_resp = re.sub(r'```json|```', '', text_resp).strip()
                
            scenes = json.loads(text_resp)
            print(f"[SceneEngine] Generated {len(scenes)} emotion-matched scenes.")
            
            # Post-process: Merge consecutive scenes with same emotion
            merged_scenes = self._merge_emotion_blocks(scenes)
            print(f"[SceneEngine] After merging: {len(merged_scenes)} visual blocks.")
            
            return merged_scenes
            
        except Exception as e:
            print(f"❌ [SceneEngine] Analysis Failed: {e}")
            traceback.print_exc()
            # Fallback: Use neutral human-focused visuals
            return [{
                "text": script_text,
                "emotion": "neutral",
                "energy": "medium",
                "keywords": ["calm person thinking", "peaceful human movement", "focused face closeup"],
                "merge_with_previous": False,
                "reasoning": "Fallback: neutral human visuals"
            }]
    
    def _merge_emotion_blocks(self, scenes: List[Dict]) -> List[Dict]:
        """
        Merges consecutive scenes with merge_with_previous=True.
        Allows one clip to span multiple audio chunks for natural flow.
        """
        if not scenes:
            return scenes
            
        merged = [scenes[0]]
        
        for scene in scenes[1:]:
            if scene.get("merge_with_previous", False) and merged:
                # Combine text, keep keywords from first
                merged[-1]["text"] += " " + scene["text"]
            else:
                merged.append(scene)
        
        return merged
    
    def get_visual_query_for_scene(
        self, 
        scene: Dict, 
        content_type: str = "educational",
        retry_index: int = 0
    ) -> str:
        """
        Get the best visual search query for a scene based on category.
        
        Category Logic:
        - entity → domain-specific keywords
        - abstract → human emotion visuals
        - event → metaphorical motion visuals
        
        retry_index: 0 = primary, 1 = secondary, 2+ = fallback
        """
        from core.content_types import get_content_type_config, get_category_fallback, MAX_CLIP_RETRIES
        
        category = scene.get("category", "entity")
        keywords = scene.get("keywords", [])
        emotion = scene.get("emotion", "neutral")
        
        # Get content type visual rules
        ct_config = get_content_type_config(content_type)
        visual_rules = ct_config.get("visual_rules", {})
        
        # Max retries enforced
        if retry_index >= MAX_CLIP_RETRIES:
            # Use category-safe fallback
            fallback = get_category_fallback(category)
            print(f"[SceneEngine] Max retries reached. Using fallback: {fallback}")
            return fallback
        
        # Primary query (retry_index = 0)
        if retry_index == 0 and keywords:
            # For finance/crypto, add domain keywords
            if content_type == "finance" and "domain_keywords" in ct_config:
                domain_kw = ct_config["domain_keywords"]
                for kw in keywords:
                    if any(d in kw.lower() for d in domain_kw):
                        return kw  # Direct match found
            return keywords[0]
        
        # Secondary query (retry_index = 1)
        if retry_index == 1 and len(keywords) > 1:
            return keywords[1]
        
        # Tertiary / fallback based on category
        if category == "entity":
            # Domain-specific fallback
            prefer = visual_rules.get("prefer", [])
            if prefer:
                return prefer[0].replace("_", " ")
            return get_category_fallback("entity")
            
        elif category == "abstract":
            # Human emotion fallback
            return f"{emotion} person face closeup"
            
        elif category == "event":
            # Motion/metaphor fallback
            return "time lapse movement motion"
        
        # Ultimate fallback
        return get_category_fallback("neutral")
    
    def validate_clip_for_scene(
        self, 
        clip_tags: List[str], 
        scene: Dict, 
        content_type: str = "educational"
    ) -> bool:
        """
        Validates if a clip is appropriate for a scene.
        Returns False if mismatch detected → triggers retry.
        
        STRICT RULES:
        - entity → must have domain-related tags
        - abstract → must have human/face tags
        - finance → must NOT have lifestyle/party tags
        """
        from core.content_types import get_content_type_config
        
        category = scene.get("category", "entity")
        ct_config = get_content_type_config(content_type)
        avoid_tags = ct_config.get("visual_rules", {}).get("avoid", [])
        
        # Check for avoided tags
        for tag in clip_tags:
            tag_lower = tag.lower()
            for avoid in avoid_tags:
                if avoid.lower() in tag_lower:
                    print(f"[SceneEngine] Rejected clip: contains '{avoid}'")
                    return False
        
        # Category-specific validation
        if category == "abstract":
            # Must have human/face/person
            human_keywords = ["person", "human", "face", "man", "woman", "people"]
            has_human = any(h in " ".join(clip_tags).lower() for h in human_keywords)
            if not has_human:
                print(f"[SceneEngine] Rejected clip for abstract scene: no human found")
                return False
        
        # Finance content type: extra strict
        if content_type == "finance":
            lifestyle_keywords = ["party", "beach", "vacation", "fun", "dance"]
            has_lifestyle = any(l in " ".join(clip_tags).lower() for l in lifestyle_keywords)
            if has_lifestyle:
                print(f"[SceneEngine] Rejected clip for finance: lifestyle detected")
                return False
        
        return True

# Singleton Instance
scene_engine = SceneEngine()
