import tensorflow as tf
import tensorflow_hub as hub
import os

def convert_model_to_tflite(model_url, output_path):
    """
    Convert a TensorFlow Hub model to TFLite format
    
    Args:
        model_url (str): URL of the TensorFlow Hub model
        output_path (str): Path where the TFLite model should be saved
    """
    # Create a temporary directory for saved model
    saved_model_path = "temp_saved_model"
    
    # Define input shape
    input_shape = (224, 224, 3)  # Default shape for many image models
    
    # Create a simple model using the hub model
    inputs = tf.keras.Input(shape=input_shape)
    hub_model = hub.load(model_url)
    outputs = hub_model(inputs)
    model = tf.keras.Model(inputs, outputs)
    
    # Save as SavedModel
    print(f"Saving temporary SavedModel to {saved_model_path}...")
    tf.saved_model.save(model, saved_model_path)
    
    # Create TFLite converter from saved model
    print("Creating TFLite converter...")
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_path)
    
    # Set optimization flags
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float32]
    
    # Enable additional optimizations if needed
    converter.allow_custom_ops = True
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    
    # Convert model
    print("Converting model to TFLite format...")
    tflite_model = converter.convert()
    
    # Save the TFLite model
    print(f"Saving TFLite model to {output_path}...")
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    # Clean up temporary saved model
    print("Cleaning up temporary files...")
    if os.path.exists(saved_model_path):
        import shutil
        shutil.rmtree(saved_model_path)
    
    print("Conversion completed successfully!")
    return output_path

# Example usage
def main():
    try:
        # You can replace this with your model URL
        model_url = "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/4"
        output_path = "converted_model.tflite"
        
        converted_path = convert_model_to_tflite(model_url, output_path)
        print(f"Model successfully converted and saved to: {converted_path}")
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        import traceback
        print("\nDetailed error information:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()