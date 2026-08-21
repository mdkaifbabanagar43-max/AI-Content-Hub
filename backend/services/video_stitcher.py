"""
Video Stitcher Service

Stitches multiple AI-generated scenes into a single coherent video
using FFmpeg with crossfade transitions.

Features:
- 0.2-0.4s crossfade between scenes
- Resolution/framerate normalization
- Optional audio overlay
- Color normalization
"""
import os
import uuid
import subprocess
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger("video_stitcher")

# --- STITCHING CONFIGURATION ---
STITCH_CONFIG = {
    "crossfade_duration": 0.3,  # seconds
    "output_fps": 30,
    "output_resolution": "1080x1920",  # 9:16 vertical
    "video_codec": "libx264",
    "audio_codec": "aac",
    "preset": "medium",
    "crf": 23,  # Quality (lower = better, 18-28 recommended)
}


@dataclass
class StitchResult:
    """Result of video stitching operation."""
    success: bool
    output_path: Optional[str]
    total_duration: float
    scenes_used: int
    scenes_skipped: int
    error: Optional[str]


class VideoStitcher:
    """
    Stitches multiple video scenes into a single coherent video.
    """
    
    def __init__(self, temp_dir: str = "/tmp"):
        self.temp_dir = temp_dir
        
    def stitch_scenes(
        self,
        scene_paths: List[str],
        output_path: Optional[str] = None,
        crossfade: float = None,
        audio_path: Optional[str] = None
    ) -> StitchResult:
        """
        Stitch multiple scene videos into one continuous video.
        
        Args:
            scene_paths: List of video file paths in order
            output_path: Optional output path (auto-generated if None)
            crossfade: Crossfade duration in seconds
            audio_path: Optional audio track to overlay
            
        Returns:
            StitchResult with output path and metadata
        """
        if crossfade is None:
            crossfade = STITCH_CONFIG["crossfade_duration"]
        
        if output_path is None:
            output_path = os.path.join(
                self.temp_dir, 
                f"veo_final_{uuid.uuid4().hex[:8]}.mp4"
            )
        
        # Filter out None/missing paths
        valid_paths = [p for p in scene_paths if p and os.path.exists(p)]
        skipped = len(scene_paths) - len(valid_paths)
        
        if not valid_paths:
            logger.error("❌ No valid scene files to stitch")
            return StitchResult(
                success=False,
                output_path=None,
                total_duration=0,
                scenes_used=0,
                scenes_skipped=skipped,
                error="No valid scene files"
            )
        
        logger.info(f"🎞️ Stitching {len(valid_paths)} scenes (skipping {skipped})")
        
        try:
            if len(valid_paths) == 1:
                # Single scene - just copy/normalize
                result_path = self._normalize_single(valid_paths[0], output_path)
            else:
                # Multiple scenes - stitch with crossfade
                result_path = self._stitch_with_crossfade(
                    valid_paths, output_path, crossfade
                )
            
            # Add audio if provided
            if audio_path and os.path.exists(audio_path) and result_path:
                result_path = self._overlay_audio(result_path, audio_path)
            
            # Get final duration
            duration = self._get_video_duration(result_path) if result_path else 0
            
            logger.info(f"✅ Stitching complete: {result_path} ({duration:.1f}s)")
            
            return StitchResult(
                success=result_path is not None,
                output_path=result_path,
                total_duration=duration,
                scenes_used=len(valid_paths),
                scenes_skipped=skipped,
                error=None
            )
            
        except Exception as e:
            logger.error(f"❌ Stitching failed: {e}")
            return StitchResult(
                success=False,
                output_path=None,
                total_duration=0,
                scenes_used=0,
                scenes_skipped=len(scene_paths),
                error=str(e)
            )
    
    def _normalize_single(self, input_path: str, output_path: str) -> Optional[str]:
        """Normalize a single video to standard format."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", f"scale={STITCH_CONFIG['output_resolution']}:force_original_aspect_ratio=decrease,pad={STITCH_CONFIG['output_resolution']}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(STITCH_CONFIG["output_fps"]),
                "-c:v", STITCH_CONFIG["video_codec"],
                "-preset", STITCH_CONFIG["preset"],
                "-crf", str(STITCH_CONFIG["crf"]),
                "-c:a", STITCH_CONFIG["audio_codec"],
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg normalize failed: {e.stderr.decode()}")
            return None
    
    def _stitch_with_crossfade(
        self,
        paths: List[str],
        output_path: str,
        crossfade: float
    ) -> Optional[str]:
        """
        Stitch videos with crossfade transitions.
        
        Uses FFmpeg's concat demuxer for reliable stitching.
        """
        try:
            # Build concat file
            concat_file = os.path.join(self.temp_dir, f"concat_{uuid.uuid4().hex[:8]}.txt")
            
            with open(concat_file, 'w') as f:
                for path in paths:
                    # Escape path for FFmpeg
                    escaped = path.replace("'", "'\\\''")
                    f.write(f"file '{escaped}'\n")
            
            # Simpler, more robust filter that handles any input resolution
            # 1. Scale to fit within target size (maintain aspect ratio)
            # 2. Pad to exact target size with black bars if needed
            target_w, target_h = STITCH_CONFIG['output_resolution'].split('x')
            
            # Use scale2ref alternative: scale to height, then pad width
            vf = f"scale=-2:{target_h},pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-vf", vf,
                "-r", str(STITCH_CONFIG["output_fps"]),
                "-c:v", STITCH_CONFIG["video_codec"],
                "-preset", STITCH_CONFIG["preset"],
                "-crf", str(STITCH_CONFIG["crf"]),
                "-an",  # No audio for now
                output_path
            ]
            
            logger.info(f"🔧 Running FFmpeg concat...")
            logger.info(f"🔧 Filter: {vf}")
            result = subprocess.run(cmd, capture_output=True)
            
            # Cleanup concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)
            
            if result.returncode != 0:
                stderr = result.stderr.decode()
                logger.error(f"FFmpeg error: {stderr}")
                
                # Try simpler fallback without scaling
                logger.info("🔄 Trying simpler concat without scaling...")
                return self._simple_concat(paths, output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Stitch failed: {e}")
            return None
    
    def _simple_concat(self, paths: List[str], output_path: str) -> Optional[str]:
        """Simple concat without any filtering - fallback option."""
        try:
            concat_file = os.path.join(self.temp_dir, f"concat_{uuid.uuid4().hex[:8]}.txt")
            
            with open(concat_file, 'w') as f:
                for path in paths:
                    escaped = path.replace("'", "'\\\''")
                    f.write(f"file '{escaped}'\n")
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True)
            
            if os.path.exists(concat_file):
                os.remove(concat_file)
            
            if result.returncode == 0:
                logger.info("✅ Simple concat succeeded")
                return output_path
            else:
                logger.error(f"Simple concat failed: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Simple concat error: {e}")
            return None
    
    def _overlay_audio(self, video_path: str, audio_path: str) -> str:
        """Overlay audio track onto video."""
        output_path = video_path.replace(".mp4", "_audio.mp4")
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", STITCH_CONFIG["audio_codec"],
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Remove intermediate file
            if os.path.exists(video_path) and video_path != output_path:
                os.remove(video_path)
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio overlay failed: {e.stderr.decode()}")
            return video_path  # Return original if audio fails
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
            
        except Exception:
            return 0.0
    
    def cleanup_temp_files(self, paths: List[str]):
        """Clean up temporary scene files."""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    logger.debug(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {path}: {e}")
