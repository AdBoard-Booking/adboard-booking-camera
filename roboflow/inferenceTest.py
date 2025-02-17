# Import the InferencePipeline object
from inference import InferencePipeline
import cv2
from inference.core.interfaces.camera.entities import VideoFrame
import supervision as sv

# create a bounding box annotator and label annotator to use in our custom sink
label_annotator = sv.LabelAnnotator()
box_annotator = sv.BoxAnnotator()
 

def my_custom_sink(predictions: dict, video_frame: VideoFrame):
    # get the text labels for each prediction
    labels = [p["class"] for p in predictions["predictions"]]
    # load our predictions into the Supervision Detections api
    detections = sv.Detections.from_inference(predictions)
    # annotate the frame using our supervision annotator, the video_frame, the predictions (as supervision Detections), and the prediction labels
    image = label_annotator.annotate(
        scene=video_frame.image.copy(), detections=detections, labels=labels
    )
    image = box_annotator.annotate(image, detections=detections)
    # display the annotated image
    cv2.imshow("Predictions", image)
    cv2.waitKey(1)

# initialize a pipeline object
pipeline = InferencePipeline.init(
    api_key="4GwHwTe95G55Xx9bWOOw",
    model_id="yolov8n-1280",
    video_reference=0, # Path to video, device id (int, usually 0 for built in webcams), or RTSP stream url
    max_fps=30,
    on_prediction=my_custom_sink,
)
pipeline.start() #start the pipeline
pipeline.join() #wait for the pipeline thread to finish