import pytest
from unittest.mock import patch, MagicMock
from services.asset_generator import generate_character_reference
from config import ModelRoutingConfig

def test_generate_character_reference_gemini_success():
    """Validates successful generation using Gemini generate_content multimodal path."""
    mock_client = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"fake_jpeg_image_bytes_gemini"
    mock_part.inline_data.mime_type = "image/jpeg"
    
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    
    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_client.models.generate_content.return_value = mock_response
    
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage.bucket.return_value = mock_bucket
    
    with patch("services.asset_generator.genai.Client", return_value=mock_client), \
         patch("services.asset_generator.get_storage_client", return_value=mock_storage), \
         patch("services.asset_generator.FIREBASE_BUCKET", "test-bucket"):
        
        uri = generate_character_reference(
            character_description="Padlock Lead Character",
            user_id="user_123",
            project_id="proj_456",
            character_id="char_789"
        )
        
        assert uri is not None
        assert uri.startswith("gs://test-bucket/users/user_123/projects/proj_456/characters/char_789/canonical_ref_")
        assert uri.endswith(".jpg")
        mock_client.models.generate_content.assert_called_once()
        mock_blob.upload_from_filename.assert_called_once()

def test_generate_character_reference_imagen_success():
    """Validates successful generation when an imagen- model is configured."""
    mock_client = MagicMock()
    mock_image = MagicMock()
    mock_image.image.image_bytes = b"fake_jpeg_image_bytes_imagen"
    
    mock_response = MagicMock()
    mock_response.generated_images = [mock_image]
    mock_client.models.generate_images.return_value = mock_response
    
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage.bucket.return_value = mock_bucket
    
    with patch("services.asset_generator.CANDIDATE_IMAGE_MODELS", ["imagen-3.0-generate-002"]), \
         patch("services.asset_generator.genai.Client", return_value=mock_client), \
         patch("services.asset_generator.get_storage_client", return_value=mock_storage), \
         patch("services.asset_generator.FIREBASE_BUCKET", "test-bucket"):
        
        uri = generate_character_reference(character_description="Imagen Character")
        assert uri is not None
        assert uri.startswith("gs://test-bucket/assets/ref_")
        mock_client.models.generate_images.assert_called_once()

def test_generate_character_reference_fallback_to_next_candidate():
    """Validates that candidate model failure cleanly tries next candidate."""
    mock_client = MagicMock()
    # First model raises exception, second model succeeds
    mock_part = MagicMock()
    mock_part.inline_data.data = b"fallback_jpeg_bytes"
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_success_response = MagicMock()
    mock_success_response.candidates = [mock_candidate]
    
    mock_client.models.generate_content.side_effect = [
        Exception("Model 1 unavailable 404"),
        mock_success_response
    ]
    
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage.bucket.return_value = mock_bucket
    
    with patch("services.asset_generator.CANDIDATE_IMAGE_MODELS", ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]), \
         patch("services.asset_generator.genai.Client", return_value=mock_client), \
         patch("services.asset_generator.get_storage_client", return_value=mock_storage), \
         patch("services.asset_generator.FIREBASE_BUCKET", "test-bucket"):
        
        uri = generate_character_reference(character_description="Fallback Character")
        assert uri is not None
        assert mock_client.models.generate_content.call_count == 2

def test_generate_character_reference_all_fail_returns_none():
    """Validates that if all candidate models fail, None is returned gracefully."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("All models unavailable")
    
    with patch("services.asset_generator.genai.Client", return_value=mock_client):
        uri = generate_character_reference(character_description="Failed Character")
        assert uri is None
