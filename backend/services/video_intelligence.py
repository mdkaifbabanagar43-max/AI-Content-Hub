
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

class SmartCropper:
    def __init__(self):
        # MediaPipe Removed
        pass

    def detect_scenes(self, video_path, threshold=27.0):
        """
        Detects scene changes in a video using PySceneDetect.
        Returns a list of start timestamps (in seconds) for each scene.
        """
        print(f"🎬 Detecting Scenes for: {video_path}")
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))

        # Improve processing speed by downscaling
        video_manager.set_downscale_factor()
        
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()
        
        print(f"✅ Found {len(scene_list)} scenes.")
        
        # Extract just the start times (seconds)
        cuts = [scene[0].get_seconds() for scene in scene_list]
        return cuts

    def snap_to_scene(self, start_time, end_time, video_path, range_buffer=1.5):
        """
        Adjusts start_time and end_time to the nearest scene boundary 
        if within 'range_buffer' seconds.
        """
        scenes = self.detect_scenes(video_path)
        if not scenes:
            return start_time, end_time
            
        print(f"📏 Snapping {start_time}-{end_time} to nearest scenes...")
        
        # 1. Snap Start
        nearest_start = min(scenes, key=lambda x: abs(x - start_time))
        if abs(nearest_start - start_time) < range_buffer:
            print(f"   -> Start snapped from {start_time} to {nearest_start}")
            start_time = nearest_start
            
        # 2. Snap End
        nearest_end = min(scenes, key=lambda x: abs(x - end_time))
        if abs(nearest_end - end_time) < range_buffer:
             print(f"   -> End snapped from {end_time} to {nearest_end}")
             end_time = nearest_end
             
        return start_time, end_time

    def detect_faces(self, frame_image):
        # Stub for now
        return []

    def get_crop_coordinates(self, video_path, timestamp, mode="center"):
        # Default to Center
        return 0.5
