from keras.models import load_model
import cv2
import os
import numpy as np
from PIL import Image
from keras import backend as K
from keras.models import Sequential
from keras.layers import Input, Dropout, Flatten, Conv2D, MaxPooling2D, Dense, Activation
from keras.optimizers import RMSprop
from keras.callbacks import ModelCheckpoint, Callback, EarlyStopping
from keras.utils import np_utils
from keras.preprocessing.image import ImageDataGenerator
import tensorflow as tf
from keras import backend as K
import pickle
optimizer = RMSprop(lr=1e-3)
objective = 'categorical_crossentropy'

# model = load_model(os.path.abspath('./python_utils/full_model.h5'))

def mathsymbol():
    model = Sequential()
    model.add(Conv2D(32, (5, 5), input_shape=(45, 45, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.2))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dense(28, activation='softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    return model

# def skeletonize(img):
#     size = np.size(img)
#     skel = np.zeros(img.shape,np.uint8)

#     ret,img = cv2.threshold(img,127,255,0)
#     element = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
#     done = False

#     while( not done):
#         eroded = cv2.erode(img,element)
#         temp = cv2.dilate(eroded,element)
#         temp = cv2.subtract(img,temp)
#         skel = cv2.bitwise_or(skel,temp)
#         img = eroded.copy()

#         zeros = size - cv2.countNonZero(img)
#         if zeros==size:
#             done = True

#     return skel

def predict_image(imgPath, imageNumber):
    K.clear_session()
    model = mathsymbol()
    model.load_weights(os.path.abspath('./python_utils/full_model.h5'))

    # img = Image.open(imgPath)
    # print("Path "+imgPath)
    # print("Shape "+str(img.shape))
    # x, y = img.size
    # print("x,y "+ str(x) + str(y))
    # imgTemp = Image.new("RGB", ( (3*max(x,y))//2, (3*max(x,y))//2), (255,255,255))
    # imgTemp.paste(img, (((3*max(x,y))//2-x)//2,((3*max(x,y))//2-y)//2))
    # imgTemp.save(imgPath)
    img = cv2.imread(imgPath)
    # print("Shape r "+str(img.shape))
    
    img = cv2.resize(img, (45,45))
    # print("Shape resize "+str(img.shape))
    
    # img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 115, 1)

    # img = cv2.bitwise_not(img)
    # img = skeletonize(img)
    # img = cv2.bitwise_not(img)
    # print("Shape "+str(img.shape))
    
    cv2.imwrite('./Images/final/final_'+str(imageNumber)+'.jpg',img)
    # img = cv2.imread('./Images/final/final_'+str(imageNumber)+'.jpg')
    
    img = np.reshape(img, (1,45,45,3))

    prediction = model.predict(img)
    L = ['(', ')', '+', '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '=', 'a', 'alpha', 'b', 'beta', 'c', 'e', 'i', 'j', 'k', 'pi', 'x', 'y', 'z']
    ans = L[np.argmax(prediction)]

    return ans

