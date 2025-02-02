import tensorflow as tf



# Convert the model
converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir) # path to the SavedModel directory
tflite_model = converter.convert()

# Save the model.
with open('model.tflite', 'wb') as f:
  f.write(tflite_model)


#  tflite_convert \
#     --saved_model_dir=/tmp/mobilenet_saved_model \
#     --output_file=/tmp/mobilenet.tflite