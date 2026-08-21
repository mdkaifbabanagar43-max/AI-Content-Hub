import os
import cv2
import json
import re
from typing import List, Tuple
from moviepy.editor import VideoFileClip
from scenedetect import detect, ContentDetector
from pydantic import BaseModel, Field

from core.models.source_analysis import (
    SourceMediaMetadata,
    SourceSceneSegment,
    SceneSemanticAnalysis,
    HookAnalysis,
    CTAAnalysis,
    SourceAudioProfile,
    SourceDialogueBeat,
    SourceVisualStyle,
    SourceAnalysis
)
from config import ModelRoutingConfig
from services.ai_service import get_gemini_client
from google.genai import types

class GeminiSemanticResponse(BaseModel):
    semantic_scenes: List[SceneSemanticAnalysis] = Field(description="List of scenes matching the provided segment timestamps")
    hook: HookAnalysis = Field(description="Analysis of the hook")
    cta: CTAAnalysis = Field(description="Analysis of the call to action")
    visual_style: SourceVisualStyle = Field(description="Analysis of the visual style")
    audio_profile: SourceAudioProfile = Field(description="Analysis of the audio landscape")
    transcript_text: str = Field(description="Complete raw transcript text")
    dialogue_beats: List[SourceDialogueBeat] = Field(description="Detailed dialogue beats mapped to roles")

def probe_media_metadata(video_path: str) -> SourceMediaMetadata:
    """Extracts true metadata facts from the media file."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    file_size_bytes = os.path.getsize(video_path)
    
    # 1. Probe with OpenCV for exact video parameters
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"OpenCV could not open video: {video_path}")
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration_seconds = frame_count / fps if fps > 0 else 0.0
    cap.release()
    
    # Calculate aspect ratio
    def gcd(a, b): return a if b == 0 else gcd(b, a % b)
    r = gcd(width, height) if width > 0 and height > 0 else 1
    w_ratio = width // r
    h_ratio = height // r
    
    # Common simplified standards
    if (w_ratio, h_ratio) in [(16, 9), (9, 16), (4, 3), (3, 4), (1, 1), (21, 9)]:
        aspect_ratio = f"{w_ratio}:{h_ratio}"
    elif width > 0 and height > 0:
        ratio_val = width / height
        if abs(ratio_val - (16/9)) < 0.02:
            aspect_ratio = "16:9"
        elif abs(ratio_val - (9/16)) < 0.02:
            aspect_ratio = "9:16"
        elif abs(ratio_val - (4/3)) < 0.02:
            aspect_ratio = "4:3"
        elif abs(ratio_val - 1.0) < 0.02:
            aspect_ratio = "1:1"
        else:
            aspect_ratio = f"{w_ratio}:{h_ratio}"
    else:
        aspect_ratio = "UNKNOWN"
        
    # 2. Probe with MoviePy for definitive audio check and precise duration
    has_audio = False
    audio_duration = None
    try:
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            has_audio = True
            audio_duration = clip.audio.duration
        # Prefer moviepy duration if valid, otherwise fallback to cv2
        if clip.duration and clip.duration > 0:
            duration_seconds = clip.duration
        clip.close()
    except Exception as e:
        print(f"[SourceAnalyzer WARNING] MoviePy probing encountered error: {e}")
        
    return SourceMediaMetadata(
        duration_seconds=round(duration_seconds, 3),
        width=width,
        height=height,
        fps=round(fps, 2),
        aspect_ratio=aspect_ratio,
        has_audio=has_audio,
        audio_duration_seconds=round(audio_duration, 3) if audio_duration else None,
        file_size_bytes=file_size_bytes
    )

def detect_scene_segments(video_path: str, duration_seconds: float) -> List[SourceSceneSegment]:
    """Uses PySceneDetect to find physical visual cuts."""
    scene_list = detect(video_path, ContentDetector(threshold=27.0))
    segments = []
    
    # If no cuts were detected, the entire video is 1 scene
    if not scene_list:
        segments.append(SourceSceneSegment(
            scene_number=1,
            start_seconds=0.0,
            end_seconds=duration_seconds,
            duration_seconds=duration_seconds,
            detection_method="VISUAL"
        ))
        return segments

    for i, scene in enumerate(scene_list):
        start = scene[0].seconds if hasattr(scene[0], "seconds") else scene[0].get_seconds()
        end = scene[1].seconds if hasattr(scene[1], "seconds") else scene[1].get_seconds()
        segments.append(SourceSceneSegment(
            scene_number=i + 1,
            start_seconds=round(start, 3),
            end_seconds=round(end, 3),
            duration_seconds=round(end - start, 3),
            detection_method="VISUAL"
        ))
    
    # Handle possible gap from 0.0 to first scene if scenedetect starts late
    if segments and segments[0].start_seconds > 0.1:
        # Shift or prepend
        first_seg = segments[0]
        first_seg.duration_seconds = round(first_seg.end_seconds - 0.0, 3)
        first_seg.start_seconds = 0.0

    # Ensure last scene reaches the end
    if segments and duration_seconds - segments[-1].end_seconds > 0.1:
        last_seg = segments[-1]
        last_seg.end_seconds = duration_seconds
        last_seg.duration_seconds = round(duration_seconds - last_seg.start_seconds, 3)

    return segments

def analyze_semantics(video_path: str, segments: List[SourceSceneSegment]) -> GeminiSemanticResponse:
    """Uses Gemini to fill in semantic data mapped to deterministic segments."""
    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        video_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
    except Exception as e:
        raise ValueError(f"Could not read video file: {e}")

    # Create a contextual prompt that enforces the strict timestamps we already found
    segment_context = "Detected Scene Segments (DO NOT INVENT YOUR OWN TIMESTAMPS FOR SCENES, USE THESE):\n"
    for s in segments:
        segment_context += f"Scene {s.scene_number}: {s.start_seconds}s to {s.end_seconds}s (Duration: {s.duration_seconds}s)\n"

    prompt = f"""
    You are a Master Viral Content Strategist and Cinematographer.
    Analyze this trending video carefully. 

    {segment_context}
    
    You MUST output strict JSON matching the provided schema.
    For the `semantic_scenes` list, provide EXACTLY {len(segments)} entries, each corresponding 1:1 with the Scene Segments listed above. Do not alter the scene_number sequence.
    Do not invent your own shot cuts. Just describe what happens in the given timeframe.
    For character roles, use generic terms like 'PROTAGONIST'. Do not assign IDs like CHAR_001.
    """

    client = get_gemini_client()
    
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeminiSemanticResponse
    )

    primary_model = ModelRoutingConfig.SOURCE_ANALYSIS
    fallback_model = ModelRoutingConfig.NORMAL_STORY

    try:
        response = client.models.generate_content(
            model=primary_model,
            contents=[video_part, prompt],
            config=generation_config
        )
    except Exception as e:
        print(f"[SourceAnalyzer] Gemini {primary_model} failed, falling back: {e}")
        response = client.models.generate_content(
            model=fallback_model,
            contents=[video_part, prompt],
            config=generation_config
        )

    try:
        cleaned = re.sub(r'```json|```', '', response.text).strip()
        data = json.loads(cleaned)
        # Parse into Pydantic model for validation
        semantic_response = GeminiSemanticResponse(**data)
        return semantic_response
    except Exception as e:
        print(f"[SourceAnalyzer] Error parsing semantic analysis: {e}")
        # In case of partial failure, we still want to raise so tests catch it
        raise

from services.trend_analyzer import analyze_trend_video

def run_source_analysis(video_path: str, source_video_id: str) -> SourceAnalysis:
    """The master orchestrator for Phase 8A source video normalization."""
    # 1. Media Facts
    metadata = probe_media_metadata(video_path)
    
    # 2. Scene Boundaries
    segments = detect_scene_segments(video_path, metadata.duration_seconds)
    
    # 3. AI Semantic Interpretation
    semantics = analyze_semantics(video_path, segments)
    
    # 4. Authoritative Visual Identity from TrendAnalyzer
    print(f"[SourceAnalyzer] Extracting authoritative visual identity...")
    try:
        trend_data = analyze_trend_video(video_path)
        authoritative_art_style = trend_data.get("art_style")
        authoritative_character_design = trend_data.get("character_design")
        
        if authoritative_art_style:
            # Separate dominant visual generation style from incidental content elements
            clean_style = authoritative_art_style
            content_elem = None
            
            # Check if animated style is polluted with live-action / meme clip references
            animated_keywords = ["3d", "animation", "animated", "cartoon", "pixar", "anime", "cgi", "render", "claymation"]
            if any(k in authoritative_art_style.lower() for k in animated_keywords):
                # Isolate incidental meme/live-action notes
                if any(m in authoritative_art_style.lower() for m in ["live-action", "live action", "meme clip", "meme insert", "real human"]):
                    content_elem = "Source contains occasional meme/live-action references"
                    # Strip live-action / meme references from the generation art_style
                    clean_style = re.sub(r"(mixed|combined)?\s*(with|and)?\s*live[\s-]?action\s*(meme\s*clips?)?", "", clean_style, flags=re.IGNORECASE)
                    clean_style = re.sub(r"  +", " ", clean_style).strip(" ,.-")
                    if not clean_style:
                        clean_style = "3D Pixar-style digital animation, stylized CGI cartoon"
            
            semantics.visual_style.art_style = clean_style
            if content_elem:
                semantics.visual_style.content_elements = content_elem
                
        if authoritative_character_design:
            semantics.visual_style.character_design = authoritative_character_design
    except Exception as e:
        print(f"[SourceAnalyzer] Warning: TrendAnalyzer failed: {e}")
    
    # 5. Construct Final Normalized Model
    return SourceAnalysis(
        source_video_id=source_video_id,
        media_metadata=metadata,
        transcript_text=semantics.transcript_text,
        scenes=segments,
        semantic_scenes=semantics.semantic_scenes,
        hook=semantics.hook,
        cta=semantics.cta,
        visual_style=semantics.visual_style,
        audio_profile=semantics.audio_profile,
        dialogue_beats=semantics.dialogue_beats
    )
