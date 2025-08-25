import os
import cv2
import numpy as np
import warnings
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras import backend as K
from tensorflow.keras.layers import (
    Input, Conv2D, MaxPooling2D, Dense, Dropout,
    BatchNormalization, Activation, Reshape, LSTM, Bidirectional
)

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")

# Character set for label encoding
ALPHABETS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-' "
NUM_CHARACTERS = len(ALPHABETS) + 1  # +1 for CTC blank token


def label_to_num(label: str) -> np.ndarray:
    """
    Convert string label to numerical format based on ALPHABETS.
    """
    return np.array([ALPHABETS.find(ch) for ch in label])


def num_to_label(num: np.ndarray) -> str:
    """
    Convert numerical labels back to string format.
    Stops at -1 which indicates blank in CTC decoding.
    """
    ret = ""
    for ch in num:
        if ch == -1:
            break
        ret += ALPHABETS[ch]
    return ret


def preprocess_image(path_or_array) -> np.ndarray:
    """
    Preprocess image for model prediction:
    - Convert to grayscale
    - Resize to (256, 64)
    - Normalize to [0,1]
    - Rotate 90° clockwise
    - Add channel and batch dimensions
    """
    if isinstance(path_or_array, str):
        img = cv2.imread(path_or_array, cv2.IMREAD_GRAYSCALE)
    else:
        img = cv2.cvtColor(path_or_array, cv2.COLOR_RGB2GRAY)

    img = cv2.resize(img, (256, 64), interpolation=cv2.INTER_AREA)
    img = img.astype(np.float32) / 255.0
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    img = np.expand_dims(img, axis=-1)  # Add channel dimension
    img = np.expand_dims(img, axis=0)   # Add batch dimension
    return img


def build_model() -> Model:
    """
    Build the CNN-RNN model for handwritten text recognition.
    """
    input_data = Input(shape=(256, 64, 1))

    # Convolutional layers
    x = Conv2D(32, (3, 3), padding='same', kernel_initializer='he_normal')(input_data)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((2, 2))(x)

    x = Conv2D(64, (3, 3), padding='same', kernel_initializer='he_normal')(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((2, 2))(x)
    x = Dropout(0.3)(x)

    x = Conv2D(128, (3, 3), padding='same', kernel_initializer='he_normal')(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((1, 2))(x)
    x = Dropout(0.3)(x)

    # Reshape for RNN
    x = Reshape((64, 1024))(x)
    x = Dense(64, activation='relu', kernel_initializer='he_normal')(x)

    # Bidirectional LSTM layers
    x = Bidirectional(LSTM(256, return_sequences=True))(x)
    x = Bidirectional(LSTM(256, return_sequences=True))(x)

    # Output layer
    x = Dense(NUM_CHARACTERS, kernel_initializer='he_normal')(x)
    y_pred = Activation('softmax')(x)

    return Model(inputs=input_data, outputs=y_pred)


# Load model and weights
MODEL_WEIGHTS_PATH = os.path.join("predictor", "model", "best_model.h5")
model = build_model()
model.load_weights(MODEL_WEIGHTS_PATH)


def predict_word(img_path: str) -> str:
    """
    Predict the word from an image path using the trained model.
    """
    img = preprocess_image(img_path)
    pred = model.predict(img)
    decoded = K.get_value(
        K.ctc_decode(
            pred,
            input_length=np.ones(pred.shape[0]) * pred.shape[1],
            greedy=True
        )[0][0]
    )
    return num_to_label(decoded[0])
