"""
One-time conversion: Keras H5 weights → ONNX (.onnx)

Rebuilds the CNN architecture, loads the H5 weights, saves as SavedModel,
then converts to ONNX.

Run once:
    python -m app.convert_model
"""

import os
import sys
import numpy as np
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "models"


def convert():
    weights_path = MODEL_DIR / "cnn_model_weights.h5"
    onnx_path = MODEL_DIR / "air_writing_cnn.onnx"
    saved_model_dir = MODEL_DIR / "saved_model_tmp"

    if not weights_path.exists():
        print(f"❌ Missing model weights: {weights_path}")
        return

    if onnx_path.exists():
        print(f"ONNX model already exists at {onnx_path}")
        return

    # Suppress TF noise
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

    print("Rebuilding CNN model architecture...")

    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Flatten

    num_classes = 62  # 10 digits + 26 uppercase + 26 lowercase
    input_shape = (28, 28, 1)

    # Rebuild the exact architecture from the air-writing project's cnn_model.py
    model = Sequential([
        Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=input_shape),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax'),
    ])

    print(f"Model: {model.count_params()} parameters")

    # Load weights
    print("Loading weights...")
    model.load_weights(str(weights_path))

    # Verify
    dummy = np.zeros((1, 28, 28, 1), dtype=np.float32)
    pred = model.predict(dummy, verbose=0)
    print(f"TF prediction shape: {pred.shape}, sum: {pred.sum():.4f}")

    # Save as SavedModel first
    print("Saving as TF SavedModel...")
    model.export(str(saved_model_dir))

    # Convert SavedModel to ONNX using command line tool
    print("Converting to ONNX via tf2onnx...")
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "tf2onnx.convert",
        "--saved-model", str(saved_model_dir),
        "--output", str(onnx_path),
        "--opset", "13",
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"tf2onnx CLI failed: {result.stderr}")
        # Try alternative: direct onnx construction
        print("Falling back to direct ONNX construction...")
        _build_onnx_directly(model, onnx_path, dummy)
    else:
        print("tf2onnx CLI conversion successful!")

    # Clean up SavedModel
    import shutil
    if saved_model_dir.exists():
        shutil.rmtree(saved_model_dir)

    if onnx_path.exists():
        print(f"Saved ONNX model to {onnx_path}")
        print(f"File size: {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")

        # Verify ONNX
        print("Verifying ONNX model...")
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
        input_name = session.get_inputs()[0].name
        input_shape = list(session.get_inputs()[0].shape)
        if len(input_shape) == 4 and input_shape[1] == 1:
            # NCHW model
            verify_input = np.transpose(dummy, (0, 3, 1, 2)).astype(np.float32)
        else:
            # NHWC model
            verify_input = dummy.astype(np.float32)
        result = session.run(None, {input_name: verify_input})
        print(f"ONNX prediction shape: {result[0].shape}, sum: {result[0].sum():.4f}")
        print("✅ Conversion complete!")
    else:
        print("❌ Conversion failed. The app will fall back to TensorFlow/Keras.")


def _build_onnx_directly(tf_model, onnx_path, dummy_input):
    """Build ONNX model by extracting weights and constructing the graph manually."""
    import onnx
    from onnx import numpy_helper, TensorProto, helper

    # Extract all layer weights
    weights = {}
    for layer in tf_model.layers:
        w = layer.get_weights()
        if w:
            weights[layer.name] = w

    # Build ONNX graph
    nodes = []
    initializers = []
    
    # Layer 1: Conv2D 32 filters 3x3
    conv1_w = weights['conv2d'][0]  # (3,3,1,32) TF format
    conv1_b = weights['conv2d'][1]  # (32,)
    # TF: (H,W,C_in,C_out) -> ONNX: (C_out,C_in,H,W)
    conv1_w_onnx = np.transpose(conv1_w, (3, 2, 0, 1)).astype(np.float32)
    
    initializers.append(numpy_helper.from_array(conv1_w_onnx, 'conv1_W'))
    initializers.append(numpy_helper.from_array(conv1_b.astype(np.float32), 'conv1_B'))
    nodes.append(helper.make_node('Conv', ['input', 'conv1_W', 'conv1_B'], ['conv1_out'],
                                  kernel_shape=[3,3], pads=[0,0,0,0]))
    nodes.append(helper.make_node('Relu', ['conv1_out'], ['relu1_out']))

    # Layer 2: Conv2D 64 filters 3x3
    conv2_w = weights['conv2d_1'][0]
    conv2_b = weights['conv2d_1'][1]
    conv2_w_onnx = np.transpose(conv2_w, (3, 2, 0, 1)).astype(np.float32)
    
    initializers.append(numpy_helper.from_array(conv2_w_onnx, 'conv2_W'))
    initializers.append(numpy_helper.from_array(conv2_b.astype(np.float32), 'conv2_B'))
    nodes.append(helper.make_node('Conv', ['relu1_out', 'conv2_W', 'conv2_B'], ['conv2_out'],
                                  kernel_shape=[3,3], pads=[0,0,0,0]))
    nodes.append(helper.make_node('Relu', ['conv2_out'], ['relu2_out']))

    # MaxPooling 2x2
    nodes.append(helper.make_node('MaxPool', ['relu2_out'], ['pool_out'],
                                  kernel_shape=[2,2], strides=[2,2]))

    # Flatten
    nodes.append(helper.make_node('Flatten', ['pool_out'], ['flat_out'], axis=1))

    # Dense 128
    dense1_w = weights['dense'][0]  # (9216, 128)
    dense1_b = weights['dense'][1]  # (128,)
    initializers.append(numpy_helper.from_array(dense1_w.astype(np.float32), 'dense1_W'))
    initializers.append(numpy_helper.from_array(dense1_b.astype(np.float32), 'dense1_B'))
    nodes.append(helper.make_node('Gemm', ['flat_out', 'dense1_W', 'dense1_B'], ['dense1_out'],
                                  transB=0))
    nodes.append(helper.make_node('Relu', ['dense1_out'], ['relu3_out']))

    # Dense 62 (output) + Softmax
    dense2_w = weights['dense_1'][0]  # (128, 62)
    dense2_b = weights['dense_1'][1]  # (62,)
    initializers.append(numpy_helper.from_array(dense2_w.astype(np.float32), 'dense2_W'))
    initializers.append(numpy_helper.from_array(dense2_b.astype(np.float32), 'dense2_B'))
    nodes.append(helper.make_node('Gemm', ['relu3_out', 'dense2_W', 'dense2_B'], ['logits'],
                                  transB=0))
    nodes.append(helper.make_node('Softmax', ['logits'], ['output'], axis=1))

    # Build graph
    input_tensor = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 1, 28, 28])
    output_tensor = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 62])

    graph = helper.make_graph(nodes, 'air_writing_cnn', [input_tensor], [output_tensor], initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 8

    onnx.save(model, str(onnx_path))
    print(f"Direct ONNX construction complete: {onnx_path}")


if __name__ == "__main__":
    convert()
