import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from collections import defaultdict
import time

# Initialize YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize the video capture from RTSP stream
cap = cv2.VideoCapture("rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2")

# Initialize Supervision components
box_annotator = sv.BoxAnnotator(
    thickness=2,
    text_thickness=2,
    text_scale=1
)

# Initialize ByteTrack tracker
byte_tracker = sv.ByteTrack()

# Initialize counters for unique IDs
person_counter = defaultdict(int)
car_counter = defaultdict(int)

# Class IDs for person and car in COCO dataset
PERSON_CLASS_ID = 0
CAR_CLASS_ID = 2

# Set the desired frame rate (frames per second)
DESIRED_FPS = 5
FRAME_TIME = 1 / DESIRED_FPS

def get_hashable_id(track_id):
    if isinstance(track_id, np.ndarray):
        return tuple(track_id.flatten())
    return track_id

frame_count = 0
while True:
    start_time = time.time()

    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    # Perform inference
    results = model(frame, agnostic_nms=True)[0]
    
    # Convert YOLOv8 results to supervision Detections
    detections = sv.Detections(
        xyxy=results.boxes.xyxy.cpu().numpy(),
        confidence=results.boxes.conf.cpu().numpy(),
        class_id=results.boxes.cls.cpu().numpy().astype(int)
    )

    # Filter for persons and cars
    mask = np.isin(detections.class_id, [PERSON_CLASS_ID, CAR_CLASS_ID])
    filtered_detections = detections[mask]

    # Perform tracking
    tracks = byte_tracker.update_with_detections(filtered_detections)

    if frame_count % 100 == 0:  # Print debug info every 100 frames
        print(f"Frame {frame_count}")
        print(f"Number of tracks: {len(tracks)}")
        if tracks:
            print(f"First track: {tracks[0]}")
            print(f"First track type: {type(tracks[0])}")
            if isinstance(tracks[0], np.ndarray):
                print(f"First track shape: {tracks[0].shape}")
            print(f"First track dtype: {tracks[0].dtype}")

    # Update counters and create labels
    labels = []
    for track in tracks:
        if isinstance(track, np.ndarray) and track.shape == (6,):
            track_id, class_id, x1, y1, x2, y2 = track
            confidence = 1.0  # Assuming confidence is not provided in this format
        else:
            print(f"Unexpected track format: {track}")
            continue

        hashable_id = get_hashable_id(track_id)
        if class_id == PERSON_CLASS_ID:
            person_counter[hashable_id] += 1
            class_name = "Person"
        elif class_id == CAR_CLASS_ID:
            car_counter[hashable_id] += 1
            class_name = "Car"
        else:
            continue

        labels.append(f"{class_name} ID: {hashable_id} Conf: {confidence:.2f}")

    # Convert tracks to Detections for annotation
    if tracks:
        try:
            track_detections = sv.Detections(
                xyxy=np.array([[track[2], track[3], track[4], track[5]] for track in tracks if isinstance(track, np.ndarray) and track.shape == (6,)]),
                confidence=np.ones(len(tracks)),  # Assuming confidence is not provided
                class_id=np.array([track[1] for track in tracks if isinstance(track, np.ndarray) and track.shape == (6,)]),
                tracker_id=np.array([get_hashable_id(track[0]) for track in tracks if isinstance(track, np.ndarray) and track.shape == (6,)])
            )
        except Exception as e:
            print(f"Error creating track_detections: {e}")
            track_detections = sv.Detections.empty()
    else:
        track_detections = sv.Detections.empty()

    # Annotate and draw on frame
    frame = box_annotator.annotate(
        scene=frame, 
        detections=track_detections,
        labels=labels
    )

    # Draw counters
    cv2.putText(
        frame,
        f"Unique Persons: {len(person_counter)} Cars: {len(car_counter)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # Show the frame
    cv2.imshow("YOLOv8 Counting with ByteTrack", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Calculate the time taken for processing this frame
    process_time = time.time() - start_time

    # If processing was faster than our desired frame time, wait for the remaining time
    if process_time < FRAME_TIME:
        time.sleep(FRAME_TIME - process_time)

cap.release()
cv2.destroyAllWindows()