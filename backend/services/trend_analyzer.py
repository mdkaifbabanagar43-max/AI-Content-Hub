import json
import re
from pydantic import BaseModel, Field
from typing import List
from google.genai import types

from config import ModelRoutingConfig
from services.ai_service import get_gemini_client

class PacingScene(BaseModel):
    scene_number: int = Field(description="Sequential scene number")
    duration_seconds: int = Field(description="Estimated duration of this scene in seconds")
    visual_description: str = Field(description="Detailed breakdown of character action and environment")

class TrendAnalysis(BaseModel):
    art_style: str = Field(description="Exact rendering style (e.g., '3D Pixar-style digital animation', 'Anime', 'Live-action real human', 'Claymation')")
    character_design: str = Field(description="Detailed physical aesthetic of the characters as they appear in the video (e.g., 'Realistic toddlers in casual clothing', 'Anthropomorphic 3D cartoon animals', 'Stylized anime characters with large eyes')")
    humor_mechanism: str = Field(description="Core narrative formula (e.g., 'Role reversal meme where inanimate tools act like humans and humans act like tools')")
    source_language: str = Field(description="Primary spoken language (e.g., 'Hindi / Hinglish')")
    transcript_text: str = Field(description="Complete spoken transcript in source language")
    pacing_scenes: List[PacingScene] = Field(description="List of scenes and their pacing")

def analyze_trend_video(video_path: str) -> dict:
    """
    Analyzes a video file and enforces a strict JSON schema to extract
    the visual style, characters, humor, language, and pacing.
    """
    print(f"[Trend Analyzer] Analyzing video: {video_path}")
    
    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        video_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
    except Exception as e:
        print(f"Error reading video: {e}")
        raise ValueError(f"Could not read video file: {e}")

    prompt = """
    You are a Master Viral Content Strategist and Computer Vision Architect.
    Analyze this trending video carefully. Extract its exact pacing, visual art style, character design, humor mechanism, and spoken transcript.
    You MUST be extremely precise about the visual 'art_style' and 'character_design' because we will use this to generate prompts for a Video AI model.
    Ensure you return STRICT JSON matching the requested schema.
    """

    client = get_gemini_client()
    
    # We use GenerateContentConfig to enforce the JSON schema
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TrendAnalysis
    )

    primary_model = ModelRoutingConfig.TREND_ANALYSIS
    fallback_model = ModelRoutingConfig.NORMAL_STORY

    try:
        response = client.models.generate_content(
            model=primary_model,
            contents=[video_part, prompt],
            config=generation_config
        )
    except Exception as e:
        print(f"[Trend Analyzer] Gemini {primary_model} failed, falling back: {e}")
        response = client.models.generate_content(
            model=fallback_model,
            contents=[video_part, prompt],
            config=generation_config
        )

    try:
        # Parse the JSON string returned by Gemini
        cleaned = re.sub(r'```json|```', '', response.text).strip()
        analysis_data = json.loads(cleaned)
        print("[Trend Analyzer] Analysis complete.")
        return analysis_data
    except Exception as e:
        print(f"[Trend Analyzer] Error during Gemini analysis: {e}")
        raise
