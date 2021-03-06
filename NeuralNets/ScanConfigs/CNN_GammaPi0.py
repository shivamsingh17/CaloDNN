###################
# Helper Function #
###################

def TestDefaultParam(Config):
    def TestParamPrime(param,default=False):
        if param in Config:
            return eval(param)
        else:
            return default
    return TestParamPrime

# TestDefaultParam("param") returns either value of param or default
TestDefaultParam=TestDefaultParam(dir())

##########################
# Configuration Settings #
##########################

import random
import getopt
from DLTools.Permutator import *
import sys,argparse
from numpy import arange
import os

from multiprocessing import cpu_count
from DLTools.Utils import gpu_count

# Save location
#saveFolder = "/home/mazhang/DLKit/CaloDNN/NeuralNets/Cache/CNN_GammaPi0/"
saveFolder = "./TrainedModels/"
if not os.path.exists(os.path.dirname(saveFolder)):
    os.makedirs(os.path.dirname(saveFolder))

# Number of threads
max_threads=12
n_gpu=gpu_count()
if n_gpu>0:
    n_threads=int(min(round(cpu_count()/n_gpu),max_threads))
else:
    n_threads=max(1,cpu_count()-2)
print "Found",cpu_count(),"CPUs and",gpu_count(),"GPUs. Using",n_threads,"threads. max_threads =",max_threads

# Particle types
Particles=["Pi0","Gamma"]

# ECAL shapes (add dimensions for conv net)
ECALShape= (None, 25, 25, 25, 1)
HCALShape= (None, 5, 5, 60, 1)

# Input for mixing generator
FileSearch="/data/LCD/V2/MLDataset3D/*/*.h5"

# Config settings (to save in output directory)
Config={
    "MaxEvents":int(3.e5),
    "NTestSamples":int(3.e5 * 0.1),
    "NClasses":len(Particles),

    "Epochs":500,
    "BatchSize":1024,

    # Configures the parallel data generator that read the input.
    # These have been optimized by hand. Your system may have
    # more optimal configuration.
    "n_threads":n_threads,  # Number of workers
    "n_threads_cache":5,
    "multiplier":1, # Read N batches worth of data in each worker

    # How weights are initialized
    "WeightInitialization":"'normal'",

    # Normalization determined by hand.
    "ECAL":True,
    "ECALNorm":"'NonLinear'",

    # Normalization needs to be determined by hand. 
    "HCAL":True,
    "HCALNorm":"'NonLinear'",

    # CNN properties
    "CNNLayers":"5",

    # No specific reason to pick these. Needs study.
    # Note that the optimizer name should be the class name (https://keras.io/optimizers/)
    "loss":"'categorical_crossentropy'",
    "activation":"'relu'",
    "BatchNormLayers":True,
    "DropoutLayers":True,
    
    # Specify the optimizer class name as True (see: https://keras.io/optimizers/)
    # and parameters (using constructor keywords as parameter name).
    # Note if parameter is not specified, default values are used.
    "optimizer":"'RMSprop'",
    "lr":0.5,    
    "decay":0.001,

    # Parameter monitored by Callbacks
    "monitor":"'val_loss'",

    # Active Callbacks
    # Specify the CallBack class name as True (see: https://keras.io/callbacks/)
    # and parameters (using constructor keywords as parameter name,
    # with classname added).
    "ModelCheckpoint":True,
    "Model_Chekpoint_save_best_only":False,    

    # Configure Running time callback
    # Set RunningTime to a value to stop training after N seconds.
    "RunningTime": 24*3600,

    # Load last trained version of this model configuration. (based on Name var below)
    "LoadPreviousModel":True
}

# Add config settings to current scope
# CNNLayers = TestDefaultParam("CNNLayers",0)
# if CNNLayers is not 0:
    # CNNWidth = [None] * CNNLayers
    # CNNFeatures = [None] * CNNLayers

for a in Config:
    exec(a+"="+str(Config[a]))

###################
# Hyperparameters #
###################

# Parameters to scan and their scan points.
Params={"optimizer":["'RMSprop'","'Adam'","'SGD'"],
        "Width":[32,64,128,256,512],
        "Depth":range(1,5),
        "lr":[0.01,0.001],
        "decay":[0.01,0.001],
        }

# Get all possible configurations.
PS=Permutator(Params)
Combos=PS.Permutations()
print "HyperParameter Scan: ", len(Combos), "possible combiniations."

# HyperParameter sets are numbered. You can iterate through them using
# the -s option followed by an integer .
i=0
if "HyperParamSet" in dir():
    i=int(HyperParamSet)

for k in Combos[i]: Config[k]=Combos[i][k]

# Use the same Width and/or Depth for ECAL/HCAL if these parameters 
# "Width" and/or "Depth" are set.
if "Width" in Config:
    Config["ECALWidth"]=Config["Width"]
    Config["HCALWidth"]=Config["Width"]
if "Depth" in Config:
    Config["ECALDepth"]=Config["Depth"]
    Config["HCALDepth"]=Config["Depth"]

# Build a name for the this configuration using the parameters we are
# scanning.
Name="CaloDNN"
for MetaData in Params.keys():
    val=str(Config[MetaData]).replace('"',"")
    Name+="_"+val.replace("'","")

if "HyperParamSet" in dir():
    print "______________________________________"
    print "ScanConfiguration"
    print "______________________________________"
    print "Picked combination: ",i
    print "Combo["+str(i)+"]="+str(Combos[i])
    print "Model Filename: ",Name
    print "______________________________________"
else:
    for ii,c in enumerate(Combos):
        print "Combo["+str(ii)+"]="+str(c)

################
# Create Model #
################

from CaloDNN.NeuralNets.Models import *
trainCache = saveFolder + "Train.h5"
testCache = saveFolder + "Test.h5"
OutputBase = saveFolder + "Model" # Save folder

class ConvolutionalECAL(Convolutional3D):

    from keras.layers.core import Activation

    def Build(self):

        input=Input(self.shape[1:])

	# first conv layer and pooling 

        modelT=Conv3D(filters=64, kernel_size=3, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	modelT=MaxPooling3D(pool_size=(2, 2, 2), padding='valid', data_format=None)(modelT)

	# dimensionality reduction

        modelT=Conv3D(filters=64, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	# second conv layer and pooling 

        modelT=Conv3D(filters=192, kernel_size=3, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	modelT=MaxPooling3D(pool_size=(2, 2, 2), padding='valid', data_format=None)(modelT)

	# first inception layer

        inception_1_1x1=Conv3D(filters=64, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_3x3_reduce=Conv3D(filters=96, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_3x3=Conv3D(filters=128, kernel_size=3, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_5x5_reduce=Conv3D(filters=16, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_5x5=Conv3D(filters=32, kernel_size=5, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	inception_1_pool=MaxPooling3D(pool_size=(2, 2, 2), padding='valid', data_format=None)(modelT)

        inception_1_pool_reduce=Conv3D(filters=32, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	modelT = merge([inception_1_1x1, inception_1_3x3, inception_1_5x5, inception_1_pool_reduce], mode='concat', concat_axis=1)

	# average pooling and middle classifier

	# second inception layer

        inception_1_1x1=Conv3D(filters=64, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_3x3_reduce=Conv3D(filters=96, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_3x3=Conv3D(filters=128, kernel_size=3, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_5x5_reduce=Conv3D(filters=16, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

        inception_1_5x5=Conv3D(filters=32, kernel_size=5, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	inception_1_pool=MaxPooling3D(pool_size=(2, 2, 2), padding='valid', data_format=None)(modelT)

        inception_1_pool_reduce=Conv3D(filters=32, kernel_size=1, padding='valid', activation=self.activation, data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros')(modelT)

	modelT = merge([inception_1_1x1, inception_1_3x3, inception_1_5x5, inception_1_pool_reduce], mode='concat', concat_axis=1)

	# average pooling and end classifier

	modelT=MaxPooling3D(pool_size=(2, 2, 2), padding='valid', data_format=None)(modelT)

	

        modelT=Flatten()(modelT)
        modelT=Dropout(0.5)(modelT)



    loss1_ave_pool = AveragePooling2D(pool_size=(5,5),strides=(3,3),name='loss1/ave_pool')(inception_4a_output)
    loss1_conv = Convolution2D(128,1,1,border_mode='same',activation='relu',name='loss1/conv',W_regularizer=l2(0.0002))(loss1_ave_pool)
    loss1_flat = Flatten()(loss1_conv)
    loss1_fc = Dense(1024,activation='relu',name='loss1/fc',W_regularizer=l2(0.0002))(loss1_flat)
    loss1_drop_fc = Dropout(0.7)(loss1_fc)
    loss1_classifier = Dense(1000,name='loss1/classifier',W_regularizer=l2(0.0002))(loss1_drop_fc)
    loss1_classifier_act = Activation('softmax')(loss1_classifier)
    loss3_flat = Flatten()(pool5_7x7_s1)
    pool5_drop_7x7_s1 = Dropout(0.4)(loss3_flat)
    loss3_classifier = Dense(1000,name='loss3/classifier',W_regularizer=l2(0.0002))(pool5_drop_7x7_s1)
    loss3_classifier_act = Activation('softmax',name='prob')(loss3_classifier)
    googlenet = Model(input=input, output=[loss1_classifier_act,loss2_classifier_act,loss3_classifier_act])




        self.inputT=input
        self.modelT=modelT
        
        self.Model=Model(input,modelT)

class ConvolutionalHCAL(Convolutional3D):

    from keras.layers.core import Activation

    def Build(self):

        input=Input(self.shape[1:])
        modelT=Conv3D(filters=3, kernel_size=(2, 2, 5), strides=(1, 1, 2), padding='valid', data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros', kernel_regularizer=None, bias_regularizer=None, activity_regularizer=None, kernel_constraint=None, bias_constraint=None)(input)
        modelT=Conv3D(filters=8, kernel_size=(2, 2, 5), strides=(1, 1, 2), padding='valid', data_format=self.data_format, dilation_rate=(1, 1, 1), activation=self.activation, use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros', kernel_regularizer=None, bias_regularizer=None, activity_regularizer=None, kernel_constraint=None, bias_constraint=None)(modelT)

        modelT=Flatten()(modelT)
        modelT=Dropout(0.5)(modelT)

        self.inputT=input
        self.modelT=modelT
        
        self.Model=Model(input,modelT)

if ECAL:
    ECALModel=ConvolutionalECAL(Name+"ECAL", shape=ECALShape)
    ECALModel.Build()
    MyModel=ECALModel

if HCAL:
    HCALModel=ConvolutionalHCAL(Name+"HCAL", shape=HCALShape)
    HCALModel.Build()
    MyModel=HCALModel

if HCAL and ECAL:
    ConfigModel=MergerModel(Name+"_Merged",[ECALModel,HCALModel], NClasses, WeightInitialization,
			OutputBase=OutputBase)

ConfigModel.Loss=loss # Configure the Optimizer, using optimizer configuration parameter.
