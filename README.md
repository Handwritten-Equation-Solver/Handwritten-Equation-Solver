# Handwritten Equation Solver Application

## ToDo

- [ ] Make a Server for Digit Recognition
- [ ] Make a client App for Digit Recognition

## Technologies/Frameworks Used

- Keras
- Nodejs
- Keras-js
- Android Studio

## Prerequisites

- Kears must be installed (with TensorFlow backend)
- Nodejs must be installed
    - Run `npm init` in `Server/digit_reco_server` to install `keras-js` as well
- h5py must be installed
- Android studio must be installed

## Server

The server is built on Nodejs. The Multi-layer perceptron model is built using Keras.
<br><br>
1. Build the model using Keras
```
cd Server/digit_reco_server/keras_model
python data_gen.py
python encoder.py models_generated/model.hdf5
```

2. Start the server

## Client

ToDo