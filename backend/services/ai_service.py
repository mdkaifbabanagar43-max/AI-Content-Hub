"""
AI Service Module
Vertex AI / Gemini model handling extracted from main.py
"""
import os
import re
import json
from typing import List
from config import ModelRoutingConfig
from core.telemetry import log_model_telemetry

# --- LAZY LOADING ---
_bedrock_initialized = False
_bedrock_client = None

def _init_bedrock():
    """Initialize AWS Bedrock client (lazy, once)."""
    global _bedrock_initialized, _bedrock_client
    if not _bedrock_initialized:
        try:
            import boto3
            from botocore.config import Config
            # Assumes AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION are in env
            boto_config = Config(
                read_timeout=180,
                connect_timeout=30,
                retries={'max_attempts': 2}
            )
            _bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                config=boto_config
            )
            _bedrock_initialized = True
            print("AWS Bedrock initialized with 180s timeout")
        except Exception as e:
            print(f"AWS Bedrock Init Warning: {e}")

def _invoke_bedrock_claude(prompt: str, model_id: str, temperature: float = 0.7) -> str:
    _init_bedrock()
    if not _bedrock_client:
        raise Exception("Bedrock not initialized")
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    response = _bedrock_client.invoke_model(
        modelId=model_id,
        body=body,
        accept='application/json',
        contentType='application/json'
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body['content'][0]['text']


def route_and_generate_text(prompt: str, task: str = "NORMAL_STORY", temperature: float = 0.7) -> str:
    """
    Unified text generation with STRICT DETERMINISTIC routing based on ModelRoutingConfig.
    """
    if task == "SOURCE_ANALYSIS":
        model_id = ModelRoutingConfig.SOURCE_ANALYSIS
    elif task == "COMPLEX_STORY":
        model_id = ModelRoutingConfig.COMPLEX_STORY
    else:
        model_id = ModelRoutingConfig.NORMAL_STORY
        task = "NORMAL_STORY"
        
    print(f"[ModelRouter] Routing '{task}' task to: {model_id}")
    log_model_telemetry(
        task=task,
        provider="AWS Bedrock" if "claude" in model_id.lower() else "Google Gemini",
        model=model_id,
        reason="Deterministic Task Mapping"
    )
    
    try:
        if "claude" in model_id.lower():
            return _invoke_bedrock_claude(prompt, model_id, temperature)
        else:
            # Gemini models
            model = get_gemini_model(model_id)
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text
    except Exception as e:
        print(f"[ModelRouter] Generation Error with {model_id}: {e}")
        # Fallback to absolute base gemini
        fallback_model = ModelRoutingConfig.NORMAL_STORY
        log_model_telemetry(
            task=task,
            provider="Google Gemini",
            model=fallback_model,
            reason=f"Fallback due to {model_id} failure: {e}"
        )
        try:
            model = get_gemini_model(fallback_model)
            response = model.generate_content(prompt, generation_config={"temperature": temperature})
            return response.text
        except Exception as fallback_e:
            return f"Error generating text: {fallback_e}"

def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """Backward compatible wrapper"""
    return route_and_generate_text(prompt, task="NORMAL_STORY", temperature=temperature)

# ============================================================
# GOOGLE GEMINI — Multimodal Tasks (Vision, Video Analysis)
# ============================================================
# Gemini excels at understanding images and video content.
# Used by: Repurposer (video analysis), Vision Service (image analysis)
_gemini_client = None
GEMINI_MODEL_NAME = ModelRoutingConfig.SOURCE_ANALYSIS
GEMINI_FALLBACK_MODEL = ModelRoutingConfig.NORMAL_STORY

def get_gemini_client():
    """
    Get google-genai Client for MULTIMODAL tasks (video/image analysis).
    Text-only tasks should use generate_text() (AWS Bedrock) instead.
    """
    global _gemini_client
    if _gemini_client is None:
        PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "shortcutai-backend")
        LOCATION = "us"
        try:
            from google import genai
            _gemini_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
            print(f"Google GenAI Client initialized (Project: {PROJECT_ID}, Location: {LOCATION})")
        except Exception as e:
            print(f"Google GenAI Client Init Warning: {e}")
            raise
    return _gemini_client

# Keep get_gemini_model for backward compatibility in generate_text
class _LegacyModelWrapper:
    def __init__(self, model_name: str = ModelRoutingConfig.NORMAL_STORY):
        self.model_name = model_name

    def generate_content(self, prompt, generation_config=None):
        client = get_gemini_client()
        kwargs = {"model": self.model_name, "contents": prompt}
        if generation_config:
            from google.genai import types
            kwargs["config"] = types.GenerateContentConfig(**generation_config)
            
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            print(f"Gemini {self.model_name} failed, falling back: {e}")
            kwargs["model"] = GEMINI_FALLBACK_MODEL
            return client.models.generate_content(**kwargs)

def get_gemini_model(model_name: str = ModelRoutingConfig.NORMAL_STORY):
    return _LegacyModelWrapper(model_name)

# Aliases
get_best_model = get_gemini_model
get_vertex_model_lazy = get_gemini_model

# --- SCRIPT GENERATION ---
def generate_brainstorm_angles(topic: str, language: str = "English") -> List[dict]:
    """Generate 4 viral content angles for a topic."""
    # Force Hinglish for Hindi
    if language and "hindi" in language.lower():
        language = "Hinglish (Conversational Hindi + English)"
    
    # model = get_gemini_model() # Deprecated
    prompt = f"""
    You are a Master Viral Content Strategist for TikTok and Instagram Reels.
    Topic: '{topic}'
    Language: {language} (IMPORTANT: Generate content in this language. If 'Hindi', use 'Hinglish' - a mix of Hindi and English).
    
    GOAL: Generate 4 distinct, high-retention angles/hooks for a short vertical video (Under 60s).
    CONSTRAINT: Do NOT use emojis in the hooks/titles. Keep them professional and clean.
    
    STRATEGY:
    1. **Curiosity Gap**: "You won't believe..."
    2. **Negative Urgency**: "Stop doing this..."
    3. **Listicle**: "3 Secret Tools..."
    4. **Story**: "How I went from..."
    
    OUTPUT FORMAT (Strict JSON):
    [
      {{ "id": 1, "title": "The Dark Side of {topic}", "hook": "Stop using {topic} until you hear this.", "mood": "Urgent" }},
      {{ "id": 2, "title": "3 {topic} Hacks", "hook": "I bet you didn't know this hack.", "mood": "Fast-Paced" }}
    ]
    """
    
    try:
        response_text = generate_text(prompt)
        cleaned = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"Brainstorm Error: {e}")
        # Fallback
        return [
            {"id": 1, "title": f"⚠️ The Truth About {topic}", "hook": "Everything you know is wrong.", "mood": "Surprising"},
            {"id": 2, "title": f"🚀 {topic} Explained in 30s", "hook": "Here is the ultimate breakdown.", "mood": "Fast"}
        ]

def generate_video_ideas(topic: str, language: str = "English") -> str:
    """Generate 5 high-CTR video concepts. Returns raw JSON string."""
    if language and "hindi" in language.lower():
        language = "Hinglish (Conversational Hindi + English)"
    
    # model = get_gemini_model() # Deprecated
    prompt = f"""
    You are a World-Class YouTube & TikTok Strategist.
    The user wants a video about: '{topic}'.
    Language: {language} (Generate strictly in this language. If 'Hindi', use 'Hinglish').
    
    Generate 5 HIGH-CTR Video Concepts.
    
    CRITICAL RULES:
    1. **CURIOSITY GAPS**: Start with "The secret...", "Stop doing...", or "Why X is a lie."
    2. **CONTRARIAN TRUTHS**: Challenge common beliefs.
    3. **NO GENERIC TITLES**: Avoid "Top 5 tips for...".
    4. **HOOKS**: Must be under 10 words. Punchy. Emotional.
    
    Return RAW JSON LIST:
    [
        {{
            "title": "Why Coffee is actually killing your gains",
            "hook": "Stop drinking coffee before 9AM. Here is why."
        }}
    ]
    """
    
    response_text = generate_text(prompt)
    text = response_text
    text = re.sub(r'```json|```', '', text).strip()
    return text

def generate_script_and_visuals(
    title: str,
    hook: str = "",
    platform: str = "tiktok",
    duration: str = "30s",
    mood: str = "informative",
    voice_name: str = "en-US-Journey-D",
    language: str = "English",
    content_type: str = "educational",  # NEW: Content type
    visual_style: str = "Cinematic"
) -> dict:
    """
    Generate script preview with voiceover text and visual plan.
    Now content-type aware for better tone matching.
    Returns: {"title": str, "voiceover": str, "visual_plan": list, "scenes": list}
    """
    from core.content_types import get_content_type_config
    
    if language and "hindi" in language.lower():
        language = "Hinglish (Conversational Hindi + English)"
    
    duration_s = 60 if "60" in duration else 30
    if "90" in duration:
        duration_s = 90
    required_clips = int(duration_s / 2.5) + 3
    
    # Get content type config for tone/structure
    ct_config = get_content_type_config(content_type)
    tone = ct_config.get("tone", "informative")
    structure = ct_config.get("script_structure", "hook → explain → recap")
    
    # model = get_gemini_model() # Deprecated
    prompt = f"""
    You are a Viral Shorts Scriptwriter for 2025.
    Topic: {title}
    Platform: {platform}
    Duration: {duration} (Aim for ~{int(duration_s * 2.5)} words).
    Content Type: {content_type.upper()}
    Tone: {tone}
    Script Structure: {structure}
    Voice: {voice_name}
    Language: {language} (CRITICAL: Write strictly in {language}. If 'Hindi', use 'Hinglish').
    
    ===== SAFETY FILTER (MANDATORY) =====
    - Context MUST be current for year 2025.
    - Do NOT recommend specific financial platforms that are known to be bankrupt.
    - Focus on general principles rather than specific apps.
    
    ===== STRICT STYLE RULES =====
    1. **Conversational English Only:** Never write in 'Headlines'.
    2. **No Robot Speak:** Use filler words naturally.
    3. **Simple Grammar:** Use short, punchy sentences. Grade 5 reading level.
    4. **Forbidden Words:** 'realm', 'tapestry', 'delve', 'unleash', 'elevate'.
    
    ===== CONTENT TYPE STRUCTURE ({content_type.upper()}) =====
    Follow this structure: {structure}
    
    ===== VISUAL BRIDGE (CRITICAL) =====
    For visual_plan, generate CONCRETE, PHYSICAL scenes.
    - Generate **{required_clips} DISTINCT** visual prompts.
    - TRANSLATE abstract concepts to physical scenes.
    - User requested Visual Style (B-Roll): {visual_style}
    - Ensure EVERY scene description adheres strictly to the {visual_style} style (e.g., if Minimalist, describe clean scenes/simple backgrounds. If Cinematic, describe 4k, high quality, real footage).
    
    ===== SCENE METADATA (NEW) =====
    For each scene chunk, also provide:
    - category: "entity" (concrete objects/people), "abstract" (emotions/concepts), or "event" (actions/changes)
    - keywords: 2-3 specific search terms for stock footage
    - emotion: the feeling (confidence, fear, curiosity, hope, calm, urgency)
    - energy: low / medium / high
    
    OUTPUT JSON: 
    {{ 
        "title": "Viral Title", 
        "voiceover": "Full spoken text...", 
        "visual_plan": ["Scene 1 description", "Scene 2 description"],
        "scenes": [
            {{
                "text": "Scene 1 spoken text",
                "category": "entity",
                "keywords": ["keyword1", "keyword2"],
                "emotion": "confidence",
                "energy": "medium"
            }}
        ]
    }} 
    """
    
    try:
        # Use deterministic COMPLEX_STORY for storyboard parsing task since it requires precise JSON structure adherence.
        # But if the user prefers NORMAL_STORY, we could just stick to that unless it's genuinely complex.
        # As per instructions: "NORMAL STORY: gemini-3.1-flash", "COMPLEX STORY: us.anthropic.claude-sonnet-4-6".
        # We will use COMPLEX_STORY for script/visuals.
        response_text = route_and_generate_text(prompt, task="COMPLEX_STORY")
        cleaned = re.sub(r'```json|```', '', response_text).strip()
        result = json.loads(cleaned)
        
        # Ensure scenes exist, fallback to simple structure
        if "scenes" not in result or not result["scenes"]:
            result["scenes"] = [{
                "text": result.get("voiceover", title),
                "category": "entity",
                "keywords": [title.split()[0] if title else "topic"],
                "emotion": "neutral",
                "energy": "medium"
            }]
        
        return result
    except Exception as e:
        print(f"Script Gen Error: {e}")
        return {
            "title": title,
            "voiceover": f"Error generating script: {e}",
            "visual_plan": [title],
            "scenes": [{
                "text": title,
                "category": "entity",
                "keywords": [title],
                "emotion": "neutral",
                "energy": "medium"
            }]
        }

def clean_script_for_tts(text: str) -> str:
    """Remove stage directions and emojis from script for TTS."""
    # Remove stage directions
    text = re.sub(r"\[.*?\]|\(.*?\)|(\*.*?\*)", "", text)
    
    # Remove emojis
    text = "".join(
        c for c in text 
        if not (0x1F600 <= ord(c) <= 0x1F64F or 
                0x1F300 <= ord(c) <= 0x1F5FF or 
                0x1F680 <= ord(c) <= 0x1F6FF or 
                0x2600 <= ord(c) <= 0x26FF or 
                0x2700 <= ord(c) <= 0x27BF)
    )
    
    return text.strip()
