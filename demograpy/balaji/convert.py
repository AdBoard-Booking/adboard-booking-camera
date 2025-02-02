from tensorflow.keras.models import load_model

# Load the model in the old format (if possible)
old_model = load_model('gender_detection.model', compile=False)

# Save in H5 format
old_model.save('gender_detection.keras')
