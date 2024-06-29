import cv2
import numpy as np
import subprocess
import threading

import time
import face_recognition
from PIL import Image, ImageDraw, ImageFont

# Input RTSP stream URL
input_rtsp_url = "rtsp://adboardbooking:adboardbooking@192.168.29.204/stream2"

# Output RTSP stream details
output_rtsp_url = "rtsp://localhost:8554/stream"

class TrackedPerson:
    def __init__(self, face_id, face_location, face_encoding):
        self.face_id = face_id
        self.face_location = face_location
        self.face_encoding = face_encoding
        self.frames_since_seen = 0

tracked_persons = []
next_face_id = 0

def process_frame(frame):
    global next_face_id, tracked_persons
    
    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find all face locations and face encodings in the current frame
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Match detected faces to tracked persons
    for face_location, face_encoding in zip(face_locations, face_encodings):
        matched = False
        for person in tracked_persons:
            # Compare face encodings
            if face_recognition.compare_faces([person.face_encoding], face_encoding)[0]:
                person.face_location = face_location
                person.frames_since_seen = 0
                matched = True
                break
        
        if not matched:
            tracked_persons.append(TrackedPerson(next_face_id, face_location, face_encoding))
            next_face_id += 1
    
    # Update tracked persons and remove those not seen recently
    tracked_persons[:] = [p for p in tracked_persons if p.frames_since_seen < 10]  # Adjust threshold as needed
    for person in tracked_persons:
        person.frames_since_seen += 1
    
    # Convert to PIL Image for drawing
    pil_image = Image.fromarray(rgb_frame)
    draw = ImageDraw.Draw(pil_image)
    font = ImageFont.load_default()
    
    # Draw rectangles and IDs
    for person in tracked_persons:
        top, right, bottom, left = person.face_location
        draw.rectangle([(left, top), (right, bottom)], outline=(255, 0, 0), width=2)
        draw.text((left, top - 10), f"ID: {person.face_id}", font=font, fill=(255, 0, 0))
    
    viewer_count = len(tracked_persons)
    draw.text((10, 30), f"Viewers: {viewer_count}", font=font, fill=(0, 255, 0))
    
    # Convert back to OpenCV format
    processed_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    return processed_frame, viewer_count

def read_frames(cap, frame_queue):
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame, trying to reconnect...")
            time.sleep(1)
            cap = cv2.VideoCapture(input_rtsp_url)
            continue
        frame_queue.append(frame)
        if len(frame_queue) > 10:  # Keep only the last 10 frames
            frame_queue.pop(0)

def main():
    cap = cv2.VideoCapture(input_rtsp_url)
    frame_queue = []

    # Start frame reading thread
    threading.Thread(target=read_frames, args=(cap, frame_queue), daemon=True).start()

    # Prepare ffmpeg command
    command = [
        'ffmpeg',
        '-re',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '{}x{}'.format(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))),
        '-i', '-',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-f', 'rtsp',
        output_rtsp_url
    ]

    # Start ffmpeg process
    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    try:
        while True:
            if frame_queue:
                frame = frame_queue.pop(0)
                processed_frame, viewer_count = process_frame(frame)
                
                # Write processed frame to ffmpeg stdin
                process.stdin.write(processed_frame.tobytes())

                # Print viewer count (you could log this or send it to a database)
                print(f"Current viewers looking at billboard: {viewer_count}")

    except KeyboardInterrupt:
        print("Stopping the stream...")
    finally:
        cap.release()
        process.stdin.close()
        process.wait()

if __name__ == "__main__":
    main()