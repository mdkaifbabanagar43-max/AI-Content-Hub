"""
Scene Composer Service

Structures user input into coherent scenes and generates
Veo-ready prompts with strict character/environment consistency.

CRITICAL: Every prompt includes the GLOBAL_STYLE_BLOCK verbatim.
"""
import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("scene_composer")

# --- STYLE PRESETS ---
STYLE_PRESETS = {
    "REALISTIC": """
Visual style: realistic, social-media native
Lighting: natural daylight
Camera: handheld or smooth minimal motion
Mood: neutral to positive
Color: natural, not cinematic
Environment: modern, clean
Framing: medium or close shots preferred
Avoid: cinematic lighting, dramatic effects, fantasy visuals, avatars, lip-sync, cartoons, animation
""".strip(),

    "CARTOON_3D": """
Visual style: 3D playful animation, Pixar-style high fidelity render
Lighting: bright, soft studio lighting
Camera: smooth, dynamic camera movements
Mood: fun, energetic, cheerful
Color: vibrant, saturated, colorful
Environment: stylized 3D world, clean textures
Framing: medium shots
Avoid: photorealism, grain, noise, gritty textures, real humans
""".strip(),

    "ANIME": """
Visual style: high quality anime, 2D Japanese animation style, Makoto Shinkai style
Lighting: dramatic, atmospheric, blooming light
Camera: cinematic anime composition
Mood: emotional, atmospheric
Color: vivid, highly detailed background art
Environment: detailed anime background
Framing: wide and medium shots
Avoid: 3D render, photorealism, western cartoon style, claymation
""".strip(),

    "CLAYMATION": """
Visual style: stop-motion claymation, Aardman style, plasticine texture
Lighting: studio miniature lighting
Camera: steady with slight stop-motion jitter
Mood: quirky, handmade, tactile
Color: distinct clay colors
Environment: miniature set design
Framing: macro or close-up
Avoid: smooth CGI, 2D animation, realistic video
""".strip(),

    "VIRAL_COMEDY": """
Visual style: photorealistic 4K, VFX integration, high contrast, vibrant "Apna Bandar Dost" style
Lighting: bright, even, high-key lighting (YouTube thumbnail style)
Camera: wide angle, handheld, dynamic motion
Mood: funny, absurd, energetic, chaotic
Color: saturated, high contrast, vivid
Environment: realistic real-world setting (village, city, street)
Framing: wide shots showing full body action
Avoid: dark lighting, cinema verite, abstract, blurred background, low quality
""".strip(),

    "FACELESS": """
Visual style: cinematic B-roll, abstract visuals, nature shots, no human faces or characters
Lighting: golden hour, soft natural light, atmospheric
Camera: slow cinematic movement, drone shots, smooth tracking
Mood: peaceful, inspirational, contemplative
Color: warm color grading, soft tones, cinematic LUT
Environment: natural landscapes, cityscapes, abstract patterns, geometric shapes, water, sky, clouds
Framing: wide establishing shots, abstract close-ups of objects/nature
CRITICAL: Absolutely NO human faces, NO people, NO characters, only scenery and objects
""".strip()
}

# Default text if no style matches
DEFAULT_STYLE = "REALISTIC"

# --- NARRATIVE FLOW TEMPLATES ---
NARRATIVE_FLOW = {
    4: [  # 30s video
        ("hook", "Attention-grabbing opening that creates curiosity"),
        ("context", "What this is about - set the scene"),
        ("insight", "The main point or revelation"),
        ("closing", "Satisfying conclusion with visual payoff"),
    ],
    6: [  # 45s video
        ("hook", "Attention-grabbing opening"),
        ("context", "What this is about"),
        ("problem", "The tension or challenge"),
        ("explanation", "Breaking it down"),
        ("resolution", "The answer or solution"),
        ("closing", "Satisfying conclusion"),
    ],
    8: [  # 60s video
        ("hook", "Attention-grabbing opening"),
        ("context", "What this is about"),
        ("problem", "The tension or challenge"),
        ("exploration", "Diving deeper"),
        ("insight", "Key revelation"),
        ("reinforcement", "Strengthen the point"),
        ("climax", "Peak moment"),
        ("closing", "Satisfying conclusion"),
    ],
}

@dataclass
class SceneDefinition:
    """
    Definition of a single scene for generation.
    
    Professional Pipeline Metadata:
    - role: Narrative function (hook, context, insight, closing, etc.)
    - risk_level: Determines retry budget (high=2, low=1)
    - visual_intent: Emotional direction (calm, curiosity, tension, confidence)
    """
    index: int
    role: str  # hook | context | problem | insight | resolution | closing
    risk_level: str  # high | medium | low
    visual_intent: str  # calm | curiosity | tension | confidence
    narrative_hint: str
    action_description: str
    full_prompt: str
    duration_target: float
    
    @property
    def max_retries(self) -> int:
        """Risk-based retry budget."""
        return 2 if self.risk_level == "high" else 1


@dataclass
class JobMetrics:
    """Metrics for R&D evaluation."""
    total_scenes: int = 0
    scenes_generated: int = 0
    scenes_degraded: int = 0  # Used fallback
    total_retries: int = 0
    estimated_cost: float = 0.0
    total_time_seconds: float = 0.0
    scene_times: List[float] = None
    
    def __post_init__(self):
        if self.scene_times is None:
            self.scene_times = []
    
    def to_dict(self) -> dict:
        return {
            "total_scenes": self.total_scenes,
            "scenes_generated": self.scenes_generated,
            "scenes_degraded": self.scenes_degraded,
            "total_retries": self.total_retries,
            "estimated_cost": round(self.estimated_cost, 2),
            "total_time_seconds": round(self.total_time_seconds, 2),
            "avg_scene_time": round(sum(self.scene_times) / len(self.scene_times), 2) if self.scene_times else 0
        }


@dataclass
class VideoComposition:
    """Full video composition with all scenes."""
    job_id: str
    topic: str
    total_duration: int
    subject: str
    environment: str
    scenes: List[SceneDefinition]
    metrics: JobMetrics = None
    voice_type: str = "FEMALE_CALM"  # Default voice type for TTS
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = JobMetrics(total_scenes=len(self.scenes))


class SceneComposer:
    """
    Composes video content into structured scenes with
    consistent character and environment references.
    """
    
    def __init__(self):
        pass
    
    
    def _analyze_topic_semantics(self, topic: str) -> dict:
        """
        Analyze the topic using Gemini to extract semantic metadata.
        Returns dict with subject, environment, style, mood.
        """
        import json
        try:
            from services.ai_service import generate_text
            
            prompt = f"""
Analyze the video topic: "{topic}"

Extract the following metadata in JSON format:
1. "subject": The primary visual subject (e.g. "a glowing quantum particle", "a cute cartoon ant", "a futuristic warrior"). 
   - Rule: Use OBJECTS or CHARACTERS.
   - Rule: If it's a story, identify the main character.
2. "environment": The best visual setting (e.g. "a dark void with data streams", "a sunny meadow", "a cyberpunk city").
3. "style_key": The best visual style. MUST be one of: ["REALISTIC", "CARTOON_3D", "ANIME", "CLAYMATION", "VIRAL_COMEDY"].
   - "REALISTIC": Default for documentaries, vlogs, tech, lifestyle.
   - "CARTOON_3D": For stories, fables, kids content, upbeat explainers.
   - "ANIME": For action, Japanese themes, emotional stories.
   - "CLAYMATION": Specific artistic request.
   - "VIRAL_COMEDY": For "Apna Bandar Dost", "Hulk", absurd humor, pranks, funny animals.
4. "mood": one word emotional tone (e.g. "curious", "tense", "calm", "upbeat", "chaotic").
5. "voice_type": The best voice for narration. MUST be one of:
   - "MALE_DEEP": For Hulk, Batman, action, intense topics.
   - "MALE_NARRATOR": For stories, fables, history, documentaries.
   - "FEMALE_CALM": Default for lifestyle, tech, health, explainer (Journey-F).
   - "FEMALE_ENERGETIC": For playful, fun, high energy topics.
   - "MONSTER": For scary, horror, or specific creature voices.

JSON OUTPUT ONLY:
"""
            response_text = generate_text(prompt, temperature=0.3)
            data = json.loads(response_text.replace("```json", "").replace("```", "").strip())
            
            # Map detected style key to valid preset
            style_key = data.get("style_key", "REALISTIC").upper()
            if style_key not in STYLE_PRESETS:
                style_key = "REALISTIC"
                
            logger.info(f"🧠 Semantic Analysis: {data}")
            return {
                "subject": data.get("subject", f"the main subject of {topic}"),
                "environment": data.get("environment", "a cinematic background"),
                "style_key": style_key,
                "mood": data.get("mood", "neutral"),
                "voice_type": data.get("voice_type", "FEMALE_CALM")
            }
            
        except Exception as e:
            logger.error(f"❌ Semantic analysis failed: {e}")
            # Intelligent Fallback 
            return {
                "subject": f"the main subject of '{topic}'",
                "environment": "a cinematic background relevant to the topic",
                "style_key": "REALISTIC",
                "mood": "neutral",
                "voice_type": "FEMALE_CALM"
            }

    def structure_scenes(
        self,
        topic: str,
        duration: int = 30,
        custom_script: Optional[str] = None,
        faceless_mode: bool = True
    ) -> VideoComposition:
        """
        Structure the video into scenes based on duration.
        
        Args:
            faceless_mode: If True, use abstract/B-roll visuals without characters
        """
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        # Semantic Analysis (The "Brain")
        logger.info(f"🧠 Analyzing topic: {topic} (faceless={faceless_mode})")
        metadata = self._analyze_topic_semantics(topic)
        
        subject = metadata["subject"]
        environment = metadata["environment"]
        style_key = metadata["style_key"]
        voice_type = metadata["voice_type"]
        
        # FACELESS MODE: Override subject and style for abstract visuals
        if faceless_mode:
            style_key = "FACELESS"
            # Convert character subjects to abstract concepts
            subject = f"visual representation of '{topic}' using abstract imagery, nature, and objects"
            environment = "natural landscapes, abstract patterns, atmospheric scenes"
            logger.info(f"🎬 FACELESS MODE: Using abstract visuals")
        
        # Get style block
        style_block = STYLE_PRESETS.get(style_key, STYLE_PRESETS[DEFAULT_STYLE])
        
        # Determine scene count
        if duration <= 30:
            scene_count = 4
            target_duration = 30
        elif duration <= 45:
            scene_count = 6
            target_duration = 45
        else:
            scene_count = 8
            target_duration = 60
        
        scene_duration = target_duration / scene_count
        
        logger.info(f"📐 Structuring {target_duration}s video into {scene_count} scenes. Style: {style_key}, Voice: {voice_type}")
        
        # Get narrative flow for this duration
        flow = NARRATIVE_FLOW[scene_count]
        
        # Generate scene descriptions using LLM
        scenes = self._generate_scene_descriptions(
            topic=topic,
            subject=subject,
            environment=environment,
            flow=flow,
            scene_duration=scene_duration,
            style_block=style_block,
            custom_script=custom_script
        )
        
        return VideoComposition(
            job_id=job_id,
            topic=topic,
            total_duration=target_duration,
            subject=subject,
            environment=environment,
            scenes=scenes,
            voice_type=voice_type
        )
    
    def _generate_scene_descriptions(
        self,
        topic: str,
        subject: str,
        environment: str,
        flow: List[tuple],
        scene_duration: float,
        style_block: str,
        custom_script: Optional[str] = None
    ) -> List[SceneDefinition]:
        """
        Generate scene-by-scene descriptions using Gemini.
        """
        scenes = []
        
        try:
            from services.ai_service import generate_text
            
            # Generate all scene actions in one call for consistency
            scene_roles = "\n".join([f"{i+1}. {role}: {hint}" for i, (role, hint) in enumerate(flow)])
            
            prompt = f"""
You are creating a {len(flow)}-scene video structure for AI video generation.

TOPIC: "{topic}"
SUBJECT: {subject}
ENVIRONMENT: {environment}

NARRATIVE STRUCTURE:
{scene_roles}

RULES:
1. Each scene is ~{scene_duration:.1f} seconds
2. Describe ONLY the visual action for each scene
3. Keep descriptions to 1-2 sentences
4. Focus on physical actions, gestures, expressions
5. Do NOT mention audio, voiceover, or text
6. Do NOT introduce new characters
7. Do NOT change the environment
8. Keep actions simple and achievable for AI video generation

OUTPUT FORMAT (exactly {len(flow)} lines):
Scene 1: [action description]
Scene 2: [action description]
...

Generate the scene actions:
"""
            
            response_text = generate_text(prompt)
            scene_texts = response_text.strip().split("\n")
            
            # Parse and create scene definitions
            for i, (role, hint) in enumerate(flow):
                # Extract action from response
                if i < len(scene_texts):
                    action_line = scene_texts[i]
                    # Remove "Scene X:" prefix if present
                    action = re.sub(r'^Scene\s*\d+:\s*', '', action_line).strip()
                else:
                    action = f"{subject} continues the narrative"
                
                # Assign risk level based on role (hook & closing = high priority)
                risk_level = "high" if role in ["hook", "closing"] else "low"
                
                # Assign visual intent based on role
                visual_intent_map = {
                    "hook": "curiosity",
                    "context": "calm",
                    "problem": "tension",
                    "insight": "confidence",
                    "explanation": "calm",
                    "resolution": "confidence",
                    "exploration": "curiosity",
                    "reinforcement": "confidence",
                    "climax": "tension",
                    "closing": "calm"
                }
                visual_intent = visual_intent_map.get(role, "calm")
                
                # Build full Veo prompt with EXACT template
                full_prompt = self._build_scene_prompt(
                    subject=subject,
                    environment=environment,
                    action=action,
                    style_block=style_block
                )
                
                scenes.append(SceneDefinition(
                    index=i,
                    role=role,
                    risk_level=risk_level,
                    visual_intent=visual_intent,
                    narrative_hint=hint,
                    action_description=action,
                    full_prompt=full_prompt,
                    duration_target=scene_duration
                ))
                
                logger.info(f"📝 Scene {i+1} ({role}, risk={risk_level}): {action[:50]}...")
                
        except Exception as e:
            logger.error(f"❌ Scene generation failed: {e}")
            # Fallback: Create generic scenes
            for i, (role, hint) in enumerate(flow):
                action = f"{subject} in a moment of {role}"
                full_prompt = self._build_scene_prompt(subject, environment, action, style_block)
                risk_level = "high" if role in ["hook", "closing"] else "low"
                
                scenes.append(SceneDefinition(
                    index=i,
                    role=role,
                    risk_level=risk_level,
                    visual_intent="calm",
                    narrative_hint=hint,
                    action_description=action,
                    full_prompt=full_prompt,
                    duration_target=scene_duration
                ))
        
        return scenes
    
    def _build_scene_prompt(
        self,
        subject: str,
        environment: str,
        action: str,
        style_block: str
    ) -> str:
        """
        Build the final Veo prompt using the EXACT template.
        
        CRITICAL: Includes safety prefix and sanitization to avoid RAI content filtering.
        """
        # Sanitize inputs to avoid content policy violations
        def sanitize(text: str) -> str:
            """Remove or replace words that might trigger content filters."""
            # Words that often trigger Veo's content policy
            banned_words = [
                "kill", "murder", "death", "dead", "dying", "blood", "gore",
                "violence", "violent", "attack", "fight", "punch", "hit",
                "weapon", "gun", "knife", "sword", "bomb", "explosion",
                "naked", "nude", "sexy", "sexual", "erotic", "adult",
                "drug", "drugs", "alcohol", "drunk", "smoking",
                "scary", "horror", "terrifying", "creepy", "evil", "demon",
                "hate", "racist", "slur", "curse", "swear",
                "money", "cash", "steal", "rob", "crime", "criminal",
                "hulk", "batman", "spiderman", "ironman", "avengers",  # Copyrighted
                "disney", "marvel", "dc", "pixar", "nintendo",  # Brands
            ]
            
            result = text.lower()
            for word in banned_words:
                result = result.replace(word, "character")
            
            # Capitalize first letter
            return result.capitalize() if result else text
        
        # Apply sanitization
        safe_subject = sanitize(subject)
        safe_action = sanitize(action)
        safe_environment = sanitize(environment)
        
        # Enhanced safety prefix
        safety_prefix = "Professional video content. Safe for all audiences. No violence, no controversial content."
        
        prompt = f"""{safety_prefix}

The same {safe_subject} in the same {safe_environment}.

{safe_action}

Camera: medium shot, smooth movement.

{style_block}
"""
        return prompt.strip()
