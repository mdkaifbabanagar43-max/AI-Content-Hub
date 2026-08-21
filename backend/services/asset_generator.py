import os
import tempfile
import uuid
from typing import Optional
from google import genai
from google.genai import types
from core.storage_client import get_storage_client, FIREBASE_BUCKET
from config import ModelRoutingConfig

# Ordered list of candidate image generation models for studio references
CANDIDATE_IMAGE_MODELS = [
    ModelRoutingConfig.REFERENCE_IMAGE,
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image"
]

def generate_character_reference(
    character_desc: str = "",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    character_id: Optional[str] = None,
    character_description: Optional[str] = None
) -> Optional[str]:
    """
    Generates a canonical character portrait using Vertex AI image generation and uploads it to GCS.
    Supports both Gemini multimodal image generation (generate_content) and Imagen (generate_images).
    Returns the gs:// URI or None if all models fail.
    """
    desc = character_description or character_desc or "3D animated character"
    project_cloud = os.getenv("GOOGLE_CLOUD_PROJECT", "shortcutai-backend")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    studio_prompt = (
        f"A front-facing 3D character portrait of {desc}, "
        "vibrant 3D Pixar animated style, clean lighting, isolated neutral background"
    )
    print(f"[AssetGenerator] Generating character reference with prompt: '{studio_prompt}'")
    
    client = genai.Client(vertexai=True, project=project_cloud, location=region)
    last_err = None

    for model_name in CANDIDATE_IMAGE_MODELS:
        if not model_name:
            continue
        try:
            print(f"[AssetGenerator] Attempting image generation with model: {model_name}")
            image_bytes = None
            
            if model_name.startswith("imagen-"):
                response = client.models.generate_images(
                    model=model_name,
                    prompt=studio_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="9:16"
                    )
                )
                if response and response.generated_images:
                    image_bytes = response.generated_images[0].image.image_bytes
            else:
                # Canonical Gemini Multimodal Image Generation
                response = client.models.generate_content(
                    model=model_name,
                    contents=studio_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            output_mime_type="image/jpeg"
                        )
                    )
                )
                if response and response.candidates:
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if part.inline_data and part.inline_data.data:
                                    image_bytes = part.inline_data.data
                                    break
                        if image_bytes:
                            break
            
            if image_bytes:
                # Save locally to upload
                temp_dir = tempfile.gettempdir()
                local_path = os.path.join(temp_dir, f"ref_{uuid.uuid4().hex}.jpg")
                with open(local_path, "wb") as f:
                    f.write(image_bytes)
                    
                # Upload to GCS under project-scoped or assets folder
                storage_client = get_storage_client()
                bucket = storage_client.bucket(FIREBASE_BUCKET)
                
                if user_id and project_id and character_id:
                    gcs_blob_name = f"users/{user_id}/projects/{project_id}/characters/{character_id}/canonical_ref_{uuid.uuid4().hex[:8]}.jpg"
                else:
                    gcs_blob_name = f"assets/ref_{uuid.uuid4().hex}.jpg"
                    
                blob = bucket.blob(gcs_blob_name)
                print(f"[AssetGenerator] Uploading reference to gs://{FIREBASE_BUCKET}/{gcs_blob_name}")
                blob.upload_from_filename(local_path, content_type="image/jpeg")
                
                # Cleanup local temp
                try:
                    os.remove(local_path)
                except Exception:
                    pass
                    
                return f"gs://{FIREBASE_BUCKET}/{gcs_blob_name}"
            else:
                raise ValueError(f"No image bytes returned by model {model_name}")
                
        except Exception as e:
            print(f"[AssetGenerator WARNING] Model {model_name} failed: {e}")
            last_err = e
            continue

    print(f"[AssetGenerator ERROR] All candidate image generation models failed. Last error: {last_err}")
    return None
