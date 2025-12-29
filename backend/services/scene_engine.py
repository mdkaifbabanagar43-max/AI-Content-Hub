
import os
import re
import json
import traceback
from typing import List, Dict, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
# from google.oauth2 import service_account # Assuming init is handled in main or auto-auth

class SceneEngine:
    def __init__(self):
        # We assume vertexai.init() is called in main.py startup
        # But we can try to lazy load the model
        pass

    def _get_model(self):
        try:
             vertexai.init(project="leafy-oxide-480614-m4", location="us-central1")
        except: pass
        
        try:
             # Try Flash 2.0 first
             return GenerativeModel("gemini-2.0-flash-exp")
        except:
             return GenerativeModel("gemini-1.5-flash-001")

    def analyze_script(self, script_text: str) -> List[Dict]:
        """
        Analyzes the full script and breaks it into visual scenes with specific search queries.
        """
        print(f"[SceneEngine] Analyzing script for visuals ({len(script_text)} chars)...")
        
        prompt = f"""
        You are an expert A.I. Video Director.
        
        TASK:
        Break the following script into logical visual scenes (1-2 sentences each) and generate specific stock footage search queries for Pexels.
        
        SCRIPT:
        "{script_text}"
        
        GUIDELINES:
        1. **Segmentation**: Group sentences that share the same visual idea.
        2. **Visual Intent**: Determine the mood and action (e.g., "Frustrated man typing," "Calm sunrise").
        3. **Search Queries**: Generate 3 specific keywords strings for Pexels.
           - Format: [Subject] + [Action] + [Setting] + [Vibe]
           - BAD: "Success", "Motivation", "Business"
           - GOOD: "Confident woman walking city slow motion", "Team meeting office whiteboard", "Man running up stairs sweat"
        4. **Variety**: Ensure queries change significantly between scenes.
        
        OUTPUT FORMAT (JSON ARRAY ONLY):
        [
            {{
                "text": "The exact sentence(s) from the script.",
                "keywords": ["query 1", "query 2", "query 3"],
                "mood": "emotion",
                "subject": "main subject"
            }},
            ...
        ]
        """
        
        try:
            model = self._get_model()
            config = GenerationConfig(
                temperature=0.4,
                response_mime_type="application/json"
            )
            
            response = model.generate_content(prompt, generation_config=config)
            
            # Clean and parse
            text_resp = response.text.strip()
            # Remove markdown code blocks if present (though response_mime_type should handle it)
            if text_resp.startswith("```"):
                text_resp = re.sub(r'```json|```', '', text_resp).strip()
                
            scenes = json.loads(text_resp)
            print(f"[SceneEngine] Generated {len(scenes)} scenes.")
            return scenes
            
        except Exception as e:
            print(f"❌ [SceneEngine] Analysis Failed: {e}")
            traceback.print_exc()
            # Fallback: Return single scene with whole text
            return [{
                "text": script_text,
                "keywords": [f"cinematic {script_text[:20]}", "abstract background", "lifestyle 4k"],
                "mood": "neutral",
                "subject": "general"
            }]

# Singleton Instance
scene_engine = SceneEngine()
