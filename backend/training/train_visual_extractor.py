import os
from pathlib import Path
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

def train_visual_model():
    # Force CPU to avoid Metal GPU plugin crashes on Apple Silicon M2
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')
    
    base_dir = Path(__file__).parent.parent.parent
    train_dir = base_dir / "dataset/train"
    val_dir = base_dir / "dataset/val"
    models_dir = base_dir / "backend/models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print("TensorFlow Version:", tf.__version__)
    print("Num GPUs Available:", len(tf.config.list_physical_devices('GPU')))
    
    # 1. Image preprocessing & data loading
    # Preprocessing is handled inside the network via tf.keras.applications.efficientnet.preprocess_input
    # but we can apply slight rescaling if needed, or do it inside.
    train_datagen = ImageDataGenerator()
    val_datagen = ImageDataGenerator()
    
    train_generator = train_datagen.flow_from_directory(
        train_dir,
        target_size=(224, 224),
        batch_size=32,
        class_mode='binary',
        shuffle=True
    )
    
    val_generator = val_datagen.flow_from_directory(
        val_dir,
        target_size=(224, 224),
        batch_size=32,
        class_mode='binary',
        shuffle=False
    )
    
    print("Classes mapping:", train_generator.class_indices)
    
    # 2. Build EfficientNetB0 backbone + classifier head
    # Preprocessing layer is included inside the model so that inference doesn't require complex scaling.
    base_model = tf.keras.applications.EfficientNetB0(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # Freeze backbone first
    
    inputs = layers.Input(shape=(224, 224, 3))
    # EfficientNet has built-in preprocessing, but let's pass it through tf's standard preprocessing layer
    x = layers.Lambda(tf.keras.applications.efficientnet.preprocess_input)(inputs)
    x = base_model(x, training=False)
    features = layers.GlobalAveragePooling2D(name="feature_output")(x)
    x = layers.Dropout(0.3)(features)
    outputs = layers.Dense(1, activation='sigmoid', name="classifier_output")(x)
    
    model = models.Model(inputs, outputs)
    
    # 3. Train Head (Backbone Frozen)
    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-3),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    print("Phase 1: Training classifier head...")
    model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=5,
        verbose=1
    )
    
    # 4. Fine-Tune (Unfreeze top layers of Backbone)
    # Unfreeze the last 30 layers of the EfficientNet backbone
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False
        
    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-5), # very low learning rate for fine-tuning
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    checkpoint_path = models_dir / "receipt_feature_extractor.keras"
    
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=6, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1),
        ModelCheckpoint(filepath=str(checkpoint_path), monitor='val_loss', save_best_only=True, verbose=1)
    ]
    
    print("Phase 2: Fine-tuning backbone...")
    model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=15,
        callbacks=callbacks,
        verbose=1
    )
    
    print(f"✓ Feature extractor model trained and saved to: {checkpoint_path}")

if __name__ == "__main__":
    train_visual_model()
