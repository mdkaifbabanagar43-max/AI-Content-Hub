import os
import sys

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from viral_editor import process_dynamic_cut, get_moviepy

def test_dynamic_cut():
    print("Testing dynamic cut...")
    mp = get_moviepy()
    ColorClip = mp["ColorClip"]
    
    # Create a 2 second dummy video
    clip = ColorClip(size=(1920, 1080), color=(255, 0, 0), duration=2)
    clip.fps = 24
    
    print("Dummy video created. Running process_dynamic_cut...")
    try:
        final_clip = process_dynamic_cut(clip)
        
        # We must actually iterate frames to trigger the lazy evaluated frame generator
        print("Iterating over frames to ensure no runtime errors...")
        for frame in final_clip.iter_frames(fps=10):
            pass # Just pull frames to trigger frame_generator
            
        print("✅ SUCCESS! process_dynamic_cut executed perfectly without crashing.")
    except Exception as e:
        import traceback
        print(f"❌ ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_dynamic_cut()
