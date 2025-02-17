import cv2
from transformers import AutoModelForImageClassification, AutoImageProcessor
import torch
from PIL import Image
import requests

# Load the model and processor
model = AutoModelForImageClassification.from_pretrained("Leilab/gender_class")
processor = AutoImageProcessor.from_pretrained("Leilab/gender_class")

cap = cv2.VideoCapture(0)
                       
# Load an image
image_url = "https://example.com/your_image.jpg"  # Replace with your image URL or path
ret, frame = cap.read()

# Preprocess the image
inputs = processor(images=frame, return_tensors="pt")

# Perform inference
with torch.no_grad():
    outputs = model(**inputs)

# Get the predicted class
logits = outputs.logits
predicted_class_idx = logits.argmax(-1).item()

# Map the predicted class index to the class label
labels = model.config.id2label
predicted_label = labels[predicted_class_idx]

print(f"Predicted class: {predicted_label}")
