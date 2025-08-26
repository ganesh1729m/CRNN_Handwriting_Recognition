from django.test import TestCase
import warnings
import os

# Suppress TensorFlow INFO/WARNING
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Suppress Python warnings
warnings.filterwarnings("ignore")



from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

model = Sequential([
    Dense(64, activation="relu", input_shape=(100,)),
    Dense(10, activation="softmax")
])

model.summary()


# Create your tests here.
