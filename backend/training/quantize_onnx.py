import os
from pathlib import Path
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

def quantize_model():
    base_dir = Path(__file__).parent.parent.parent
    models_dir = base_dir / "backend/models"
    
    onnx_path = models_dir / "receipt_feature_extractor.onnx"
    quant_onnx_path = models_dir / "receipt_feature_extractor_quantized.onnx"
    
    if not onnx_path.exists():
        print(f"Error: {onnx_path} does not exist.")
        return
        
    print(f"Quantizing model from {onnx_path}...")
    quantize_dynamic(
        model_input=str(onnx_path),
        model_output=str(quant_onnx_path),
        weight_type=QuantType.QUInt8
    )
    
    print(f"✓ Quantized model saved to: {quant_onnx_path}")
    print(f"Original size: {os.path.getsize(onnx_path) / (1024 * 1024):.2f} MB")
    print(f"Quantized size: {os.path.getsize(quant_onnx_path) / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    quantize_model()
