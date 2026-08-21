import cv2
import numpy as np

def create_synthetic_video(output_path, width=640, height=360, fps=30):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Scene 1: 0 to 3 seconds (Red)
    frames_s1 = fps * 3
    red_frame = np.zeros((height, width, 3), dtype=np.uint8)
    red_frame[:] = (0, 0, 255)  # BGR
    for _ in range(frames_s1):
        out.write(red_frame)
        
    # Scene 2: 3 to 7 seconds (Green)
    frames_s2 = fps * 4
    green_frame = np.zeros((height, width, 3), dtype=np.uint8)
    green_frame[:] = (0, 255, 0)
    for _ in range(frames_s2):
        out.write(green_frame)
        
    # Scene 3: 7 to 10 seconds (Blue)
    frames_s3 = fps * 3
    blue_frame = np.zeros((height, width, 3), dtype=np.uint8)
    blue_frame[:] = (255, 0, 0)
    for _ in range(frames_s3):
        out.write(blue_frame)
        
    out.release()
    print(f"Created {output_path} successfully (10 seconds, 3 scenes).")

if __name__ == "__main__":
    create_synthetic_video("test_video.mp4")
