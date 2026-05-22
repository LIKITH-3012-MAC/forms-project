import argparse
import os
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV3Small
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

def train_cnn(data_dir, epochs=20, imgsz=224, batch=32):
    print(f"Starting CNN Transfer Learning on dataset: {data_dir}")
    
    train_dir = os.path.join(data_dir, "train")
    val_dir = os.path.join(data_dir, "val")
    
    # Data generators
    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        train_dir,
        image_size=(imgsz, imgsz),
        batch_size=batch,
        label_mode='binary'
    )
    
    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        val_dir,
        image_size=(imgsz, imgsz),
        batch_size=batch,
        label_mode='binary'
    )
    
    # Preprocessing
    preprocess_input = tf.keras.applications.mobilenet_v3.preprocess_input
    
    # Base model
    base_model = MobileNetV3Small(input_shape=(imgsz, imgsz, 3), include_top=False, weights='imagenet')
    base_model.trainable = False  # Freeze base model initially
    
    # Add top layers
    inputs = tf.keras.Input(shape=(imgsz, imgsz, 3))
    x = preprocess_input(inputs)
    x = base_model(x, training=False)
    x = GlobalAveragePooling2D()(x)
    x = Dropout(0.2)(x)
    outputs = Dense(1, activation='sigmoid')(x)
    
    model = Model(inputs, outputs)
    
    model.compile(optimizer=Adam(1e-3),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
                  
    os.makedirs("outputs/cnn_model", exist_ok=True)
    
    callbacks = [
        EarlyStopping(patience=5, restore_best_weights=True),
        ModelCheckpoint("outputs/cnn_model/best.h5", save_best_only=True)
    ]
    
    print("Phase 1: Training top layers")
    model.fit(train_ds, validation_data=val_ds, epochs=10, callbacks=callbacks)
    
    print("Phase 2: Fine-tuning entire model")
    base_model.trainable = True
    model.compile(optimizer=Adam(1e-5),  # Lower learning rate
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
                  
    model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=callbacks)
    
    print("CNN Training complete. Saved to outputs/cnn_model/best.h5")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CNN transfer learning for receipts.")
    parser.add_argument("--data", default="processed_dataset/binary", help="Path to the split dataset directory")
    parser.add_argument("--epochs", type=int, default=20, help="Number of fine-tuning epochs")
    parser.add_argument("--imgsz", type=int, default=224, help="Image size")
    parser.add_argument("--batch", type=int, default=32, help="Batch size")
    args = parser.parse_args()
    
    train_cnn(args.data, args.epochs, args.imgsz, args.batch)
