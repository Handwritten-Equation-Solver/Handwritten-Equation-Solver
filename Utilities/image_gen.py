from keras.datasets import mnist
import matplotlib.pyplot as plt

(X_train, Y_train), (X_test, Y_test) = mnist.load_data()

plt.imsave('./Images/img_0.png', X_train[0], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_10.png', X_train[10], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_100.png', X_train[100], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_5.png', X_train[5], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_15.png', X_train[15], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_20.png', X_train[20], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_105.png', X_train[105], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_110.png', X_train[110], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_120.png', X_train[120], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_1000.png', X_train[1000], format = 'png', cmap = plt.get_cmap('gray'));
plt.imsave('./Images/img_50.png', X_train[50], format = 'png', cmap = plt.get_cmap('gray'));
