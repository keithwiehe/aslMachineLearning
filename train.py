#%%
import pandas as pd
import numpy as np #numpy is for linear algebra
import os #allows for portable operating system dependant functionality
import cv2 #cv2 loads image of specified file and resize its pixel size
import tensorflow as tf #neural network 
import tensorflow.keras.optimizers as optimizers
from tqdm import tqdm #smart progress meter
import matplotlib.pyplot as plt


trainDir = "src/asl_alphabet_train/"
testDir = "src/asl_alphabet_test/"
#reduce image to size 50x50 pixels: This leaves 2500 points to use as features.
imgSize = 50
labelMapSet = {'A':0,'B':1,'C': 2, 'D': 3, 'E':4,'F':5,'G':6, 'H': 7, 'I':8, 'J':9,'K':10,'L':11, 'M': 12, 'N': 13, 'O':14, 
                'P':15,'Q':16, 'R': 17, 'S': 18, 'T':19, 'U':20,'V':21, 'W': 22, 'X': 23, 'Y':24, 'Z':25, 
                'del': 26, 'nothing': 27,'space':28}
features = imgSize * imgSize
classLabelSize = 29

#createTrainData() goes through training data and resizes the images and converts them to grayscale
def createTrainData():
  xTrain = []
  yTrain = []
  count = 0
  for folder in os.listdir(trainDir):
    print(folder)
    label = labelMapSet[folder]
    #iterate through every file in trainDir/folder(s) (e.g. src/debuggercafe/input/asl_alphabet_test/asl_alphabet_test.csv)
    for imageFile in tqdm(os.listdir(trainDir + folder)):
      count = count + 1
      path = os.path.join(trainDir, folder, imageFile)
      #resizing each image and apply grayscale
      image = cv2.resize(cv2.imread(path, cv2.IMREAD_GRAYSCALE), (imgSize, imgSize))
      xTrain.append(np.array(image))
      yTrain.append(np.array(label))
  print("Number of training images processed: %i" %(count))
  print("createTrainData finished. Returning x and y now.")
  return xTrain, yTrain

#createTestData() goes through test data and resizes the images and converts them to grayscale
def createTestData():
  xTest = []
  yTest = []
  for folder in os.listdir(testDir):
    label = folder.replace("_test.jpg", "")
    label = labelMapSet[label]
    path = os.path.join(testDir, folder)
    image = cv2.resize(cv2.imread(path, cv2.IMREAD_GRAYSCALE), (imgSize, imgSize))
    xTest.append(np.array(image))
    yTest.append(np.array(label))
  print("createTestData finished. Returning x and y test lists now.")
  return xTest, yTest

xTrain, yTrain = createTrainData()
xTest, yTest = createTestData()

#set as np array then reshape then divide
xTrain, xTest = np.array(xTrain, np.float32), np.array(xTest, np.float32)
xTrain, xTest = xTrain.reshape([-1, features]), xTest.reshape([-1, features])
xTrain, xTest = xTrain / 255., xTest / 255.


def displayImage(num):
  label = yTrain[num]
  plt.title('Label: %d' % (label))
  image = xTrain[num].reshape([imgSize, imgSize])
  plt.imshow(image, cmap=plt.get_cmap('gray_r'))
  plt.show()


# displayImage(1050)
#%%

#how much to change model in response to estimated error per update
learningRate = 0.001 
#number of epochs reminder:epochs is how many samples
trainingSteps = 8000 
#size of each iteration of training
batchSize = 250 
displayStep = 500
#number of neurons in hidden layer
nHidden = 300
#create a tensorflow dataset with slices consisting of xTrain, yTrain together
trainData = tf.data.Dataset.from_tensor_slices((xTrain, yTrain))
#repeat dataset shuffle the batch of 87000, 250(batch_size) times. : This roughly allows for more thorough data
trainData = trainData.repeat().shuffle(87000).batch(batchSize).prefetch(1)


#create the weights of each layer using the RandomNormal() API
randomNormal = tf.initializers.RandomNormal()
weights = {
  'h1': tf.Variable(randomNormal([features, nHidden])),
  'h2': tf.Variable(randomNormal([nHidden, nHidden])),
  'out': tf.Variable(randomNormal([nHidden, classLabelSize]))
}
#use the bias to shift the activation function to fit the data best. These start as zero and develop during the training
biases = {
  'b': tf.Variable(tf.zeros([nHidden])),
  'out' : tf.Variable(tf.zeros([classLabelSize]))
}

#develop the neural network with 2 hiddenlayers and the output layer
def neuralNets(inputData):
  #matmul is matrix multiplaction
  hiddenLayer1 = tf.add(tf.matmul(inputData, weights['h1']), biases['b'])
  hiddenLayer1 = tf.nn.sigmoid(hiddenLayer1)

  hiddenLayer2 = tf.add(tf.matmul(hiddenLayer1, weights['h2']), biases['b'])
  hiddenLayer2 = tf.nn.sigmoid(hiddenLayer2)
  outputLayer = tf.add(tf.matmul(hiddenLayer1, weights['out']), biases['out'])
  #softmax of outputLayer returns probabilities for each label
  return tf.nn.softmax(outputLayer)

#(ie compute_loss)loss function crossEntropy is a lograthamic scale to penalize incorrect classifications more than close classifications
def crossEntropy(yPredict, yTrue):
  yTrue = tf.one_hot(yTrue, depth=classLabelSize)
  #avoid log(0)
  yPredict = tf.clip_by_value(yPredict, 1e-9, 1.0)
  #compute crossEntropy here
  return tf.reduce_mean(-tf.reduce_sum(yTrue * tf.math.log(yPredict)))

optimizer = optimizers.Adam(learningRate)

#optimizes neural network by measuring its accuracy. This is done by matching the highest probability with the true case
def computeGradients(x, y):
  with tf.GradientTape() as tape:
    predict = neuralNets(x)
    loss = crossEntropy(predict, y)
  #use to update variables
  trainableVariables = list(weights.values()) + list(biases.values())
  #compute gradients
  gradients = tape.gradient(loss, trainableVariables)
  #zip is used to rezip gradients back into usable tuples
  # optimizer.minimize(gradients, trainableVariables)
  optimizer.apply_gradients(
    (grad, var) 
    for (grad, var) in zip(gradients,trainableVariables) 
    if grad is not None
)

def accuracy(yPredict, yTrue):
  #predicted class is the index of the highest score
  correctPrediction = tf.equal(tf.argmax(yPredict, 1), tf.cast(yTrue, tf.int64))
  return tf.reduce_mean(tf.cast(correctPrediction, tf.float32), axis=-1)


#runs the training of the neural network
for step, (batchX, batchY) in enumerate(trainData.take(trainingSteps), 1):
  #optimize weights and bias values on batch
  computeGradients(batchX, batchY)

  #print step current loss and accuracy at correct displayStep interval
  if step % displayStep == 0:
    predict = neuralNets(batchX)
    loss = crossEntropy(predict, batchY)
    acc = accuracy(predict, batchY)
    print("Training epoch: %i, Loss: %f, Accuracy: %f" %(step, loss, acc))
model = neuralNets(xTest)
print("Test Accuracy: %f" % accuracy(model, yTest))

# def getKey(val):
#   for key, value in labelMapSet.items():
#     if val == value:
#       return key

# nImages = 28
# predictions = neuralNets(xTest)
# for i in range(nImages):
#   modelPrediction = np.argmax(predictions.numpy()[i])
#   plt.imshow(np.reshape(xTest[i], [imgSize, imgSize]), cmap=plt.get_cmap('gray_r'))
#   plt.show()
#   print("Original Label: %s" % getKey(yTest[i]))
#   print("Model prediction: %s" % getKey(modelPrediction))

#%%
