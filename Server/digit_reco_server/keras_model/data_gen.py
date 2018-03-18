import numpy
from keras.datasets import mnist
from keras.utils import np_utils
import model_gen

print("\n\n----------------------------------------------\n\n")
(X_train, y_train), (X_test, y_test) = mnist.load_data()

# flatten 28*28 images to a 784 vector for each image
num_pixels = X_train.shape[1] * X_train.shape[2]
X_train = X_train.reshape(X_train.shape[0], num_pixels).astype('float32')
X_test = X_test.reshape(X_test.shape[0], num_pixels).astype('float32')

# Normalize inputs from 0-255 to 0-1
X_train = X_train / 255
X_test = X_test / 255

# One-hot encoding
y_train = np_utils.to_categorical(y_train)
y_test = np_utils.to_categorical(y_test)
num_classes = y_test.shape[1]

model = model_gen.baseline_model()

model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=10, batch_size=200, verbose=2)
print('\n\nModel Weights and Biases calculated\n\n')

scores = model.evaluate(X_test, y_test, verbose=0)
print("\n\nAccuracy Test data = " + str(scores[1]*100) + "%\n\n")

model.save_weights('./models_generated/model.hdf5')
model.save('./models_generated/full_model.hdf5')
with open('./models_generated/model.json', 'w') as f:
    f.write(model.to_json())
print("Model saved on Disk!\n\n")
print("\n\n----------------------------------------------\n\n")