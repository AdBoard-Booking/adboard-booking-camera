import cv2
from ultralytics import YOLO
import time
import supervision as sv
from collections import defaultdict
import os
from datetime import datetime


# Open the video stream (RTSP or other source)
video_path = 0

ENABLE_IMG_SHOW = True
SAVE_VIDEO_ON_DETECTION = True  # Enable saving video chunks
OUTPUT_VIDEO_DIR = "detections"  # Directory to save detected videos

# Initialize the tracker and annotator
tracker = sv.ByteTrack()

# Store unique objects and their counts
unique_objects = defaultdict(int)  # To count unique objects over time

def create_video_writer(chunk_idx, frame_size, fps):
    """Create a VideoWriter for storing the current 10-sec chunk."""
    chunk_filename = os.path.join(OUTPUT_VIDEO_DIR, f"chunk_{chunk_idx}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 codec
    return cv2.VideoWriter(chunk_filename, fourcc, fps, frame_size)

def main():
    model = YOLO("yolov8n.pt")

    # Initialize annotators
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    cap = cv2.VideoCapture(video_path)

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # Default to 30 FPS if unable to retrieve frame rate
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (frame_width, frame_height)

    print(f"Video FPS: {fps}, Resolution: {frame_size}")

    # Create output directory if not exists
    if SAVE_VIDEO_ON_DETECTION and not os.path.exists(OUTPUT_VIDEO_DIR):
        os.makedirs(OUTPUT_VIDEO_DIR)

    frame_count = 0
    chunk_idx = 1
    video_writer = create_video_writer(chunk_idx, frame_size, fps)
    last_inference_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame. Exiting...")
            time.sleep(1)
            continue

        current_time = time.time()
        if (current_time - last_inference_time) < 0.5:
            print('Skipping frame')
            continue
            
        last_inference_time = current_time
        # Perform object detection with YOLOv8
        results = model(frame, verbose=False)[0]  # Disable verbose for faster processing
        detections = sv.Detections.from_ultralytics(results)
        
        # Update tracker with detections
        detections = tracker.update_with_detections(detections)
        
        # Extract class labels and tracker IDs
        class_ids = detections.class_id
        class_labels = [model.names[class_id] for class_id in class_ids]
        tracker_ids = detections.tracker_id  # Get tracker IDs
        
        # Update unique objects count
        for cls, tid in zip(class_labels, tracker_ids):
            unique_objects[f"{cls}:{tid}"] += 1
        
        # Print detected objects
        
        current_frame_objects = [f"{cls}:#{tid}" for cls, tid in zip(class_labels, tracker_ids)]

         # Update unique objects count
        for cls, tid in zip(class_labels, tracker_ids):
            unique_objects[f"{cls}:{tid}"] += 1
        
        # Format total unique objects detected
        total_unique_objects = defaultdict(int)
        for obj in unique_objects:
            cls = obj.split(":")[0]  # Extract class name
            total_unique_objects[cls] += 1
        
        # Print total unique objects detected
        total_unique_formatted = [f"{cls}:{count}" for cls, count in total_unique_objects.items()]
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{current_time}] Current: {current_frame_objects}, Total: {total_unique_formatted}")

        # Annotate the frame
        labels = [f"{cls} #{tid}" for cls, tid in zip(class_labels, tracker_ids)]
        annotated_frame = box_annotator.annotate(scene=frame.copy(), detections=detections)
        annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)

        # Write frame to video
        if SAVE_VIDEO_ON_DETECTION:
            video_writer.write(annotated_frame)

        # Switch to a new video file every 10 seconds
        frame_count += 1
        if frame_count >= fps * 10:
            frame_count = 0
            video_writer.release()  # Close current writer
            chunk_idx += 1
            video_writer = create_video_writer(chunk_idx, frame_size, fps)

        # Display the annotated frame (if enabled)
        if ENABLE_IMG_SHOW:
            cv2.imshow("Frame", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # Cleanup
    cap.release()
    video_writer.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
