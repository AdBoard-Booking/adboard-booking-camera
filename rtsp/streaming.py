import cv2
import subprocess
import os
from ultralytics import YOLO
import supervision as sv

# Open the video stream (RTSP or other source)
video_path = 'rtsp://adboardbooking:adboardbooking@192.168.29.204:554/stream2'
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error opening video stream")
    exit()

# Get frame dimensions and FPS
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS) or 25  # Default to 25 if FPS is not detected

# Set the HLS output directory
HLS_DIR = "hls"  # Nginx serves this directory
os.makedirs(HLS_DIR, exist_ok=True)
HLS_STREAM_URL = f"{HLS_DIR}/stream.m3u8"

# FFmpeg command to convert frames into HLS stream
ffmpeg_cmd = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{frame_width}x{frame_height}',
    '-r', str(fps),
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-pix_fmt', 'yuv420p',
    '-f', 'hls',
    '-hls_time', '2',  # Each segment is 2 seconds
    '-hls_list_size', '4',  # Keep last 4 segments
    '-hls_flags', 'delete_segments',
    HLS_STREAM_URL
]

# Launch FFmpeg process
ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the tracker and annotator
tracker = sv.ByteTrack()
# box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator(text_position=sv.Position.CENTER)
# corner_annotator = sv.BoxCornerAnnotator()


while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Perform object detection with YOLOv8
    results = model(frame, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    
    # Update tracker with detections
    # detections = tracker.update_with_detections(detections)

    # Annotate the frame
    annotated_frame = label_annotator.annotate(
        scene=frame.copy(),
        detections=detections
    )


    # Write frame to FFmpeg process
    try:
        ffmpeg_process.stdin.write(annotated_frame.tobytes())
    except BrokenPipeError:
        print("FFmpeg process pipe broken")
        break

# Cleanup
cap.release()
ffmpeg_process.stdin.close()
ffmpeg_process.wait()
