import os
import tensorflow as tf
import tf2onnx
from pathlib import Path

def convert():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    extractor_path = models_dir / "receipt_feature_extractor.keras"
    onnx_path = models_dir / "receipt_feature_extractor.onnx"
    
    if not extractor_path.exists():
        print(f"Error: {extractor_path} does not exist.")
        return
        
    print(f"Loading Keras model from {extractor_path}...")
    full_model = tf.keras.models.load_model(
        str(extractor_path),
        custom_objects={'preprocess_input': tf.keras.applications.efficientnet.preprocess_input}
    )
    
    feature_layer = None
    for layer in full_model.layers:
        if layer.name == "feature_output":
            feature_layer = layer
            break
    if feature_layer is None:
        feature_layer = full_model.layers[-3]
        
    print(f"Creating sub-model up to layer: {feature_layer.name}")
    feature_model = tf.keras.Model(inputs=full_model.input, outputs=feature_layer.output)
    
    print("Converting model to ONNX...")
    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input_1"),)
    
    model_proto, _ = tf2onnx.convert.from_keras(
        feature_model,
        input_signature=spec,
        opset=13,
        output_path=str(onnx_path)
    )
    
    print(f"✓ Model successfully converted to ONNX and saved to: {onnx_path}")

if __name__ == "__main__":
    convert()
