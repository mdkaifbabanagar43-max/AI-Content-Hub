import json
import os
from pydantic import BaseModel
from typing import List, Optional
try:
    from PIL import Image
except ImportError:
    pass

from services.ai_service import get_gemini_client
from config import ModelRoutingConfig

class QualityReviewResult(BaseModel):
    character_consistency: float
    scene_adherence: float
    visual_quality: float
    continuity: float
    overall: float
    issues: List[str]
    recommended_action: str

class QualityReviewer:
    def __init__(self):
        self.client = get_gemini_client()
        
    def _extract_frames(self, video_path: str, num_frames: int = 4) -> List['Image.Image']:
        from moviepy.editor import VideoFileClip
        from PIL import Image
        clip = VideoFileClip(video_path)
        duration = clip.duration
        frames = []
        # Sample at 10%, 40%, 70%, 95%
        times = [duration * p for p in [0.1, 0.4, 0.7, 0.95]]
        for t in times:
            frame_array = clip.get_frame(t)
            img = Image.fromarray(frame_array)
            frames.append(img)
        clip.close()
        return frames

    def review_video(self, video_path: str, compiled_prompt: str, scene_quality_priority: str = "BALANCED") -> QualityReviewResult:
        """
        Extracts representative frames and asks the configured Gemini quality-review
        model to score the video against the compiled scene prompt.

        Routing (single source of truth: config.ModelRoutingConfig):
          - BALANCED priority         -> QUALITY_REVIEW
          - non-BALANCED priorities   -> QUALITY_REVIEW_ESCALATE
        """
        frames = self._extract_frames(video_path)
        
        priority_instruction = ""
        model_name = ModelRoutingConfig.QUALITY_REVIEW
        
        if scene_quality_priority != "BALANCED":
            priority_instruction = f"\nCRITICAL PRIORITY FOR THIS SCENE: {scene_quality_priority}. Please heavily emphasize issues related to this priority in your evaluation and recommended action."
            model_name = ModelRoutingConfig.QUALITY_REVIEW_ESCALATE
            
        prompt = f"""
        You are an expert AI Video Quality Inspector.
        I am providing {len(frames)} representative frames from a generated video.
        
        The video was generated using the following prompt/instructions:
        {compiled_prompt}
        {priority_instruction}
        
        Evaluate the video on these 4 dimensions (0.0 to 10.0 scale):
        1. character_consistency: Does the character match the canonical description consistently?
        2. scene_adherence: Does the video accurately depict the requested action, location, and props?
        3. visual_quality: Are there glaring rendering artifacts, anatomy issues, or camera breaking?
        4. continuity: Does the scene flow logically (if continuity constraints were provided)?
        
        CRITICAL RULES FOR STYLE CONSISTENCY:
        - If the prompt specifies a particular art style (e.g. 3D animation, anime, claymation) or non-human character design, check that the video maintains that exact aesthetic and does NOT display a mismatched style (e.g. live-action instead of animation).
        - If the generated video's visual style or character appearance fundamentally contradicts the prompt's specified character design or art style, rate character_consistency and visual_quality below 4.0 and set recommended_action to 'reject'.
        
        Provide a structured JSON output with the exact following schema:
        {{
            "character_consistency": float,
            "scene_adherence": float,
            "visual_quality": float,
            "continuity": float,
            "overall": float (average of the 4),
            "issues": ["list of major issues spotted"],
            "recommended_action": "accept" or "reject"
        }}
        
        Return ONLY valid JSON. No markdown wrappers.
        """
        
        try:
            from google.genai import types
            # Gemini SDK accepts PIL Images natively
            contents = [prompt] + frames
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            result_json = response.text
            data = json.loads(result_json)
            
            return QualityReviewResult(
                character_consistency=data.get("character_consistency", 5.0),
                scene_adherence=data.get("scene_adherence", 5.0),
                visual_quality=data.get("visual_quality", 5.0),
                continuity=data.get("continuity", 5.0),
                overall=data.get("overall", 5.0),
                issues=data.get("issues", []),
                recommended_action=data.get("recommended_action", "reject")
            )
        except Exception as e:
            print(f"[Quality Reviewer Error] {e}")
            raise RuntimeError(f"Quality reviewer failed: {e}")
