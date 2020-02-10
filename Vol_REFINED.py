# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 10:50:05 2020

@author: obazgir
"""

import csv
import numpy as np
import pandas as pd
import os
import scipy as sp
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
import cv2
import pickle
from Toolbox import NRMSE, Random_Image_Gen, two_d_norm, two_d_eq, Assign_features_to_pixels, MDS_Im_Gen, Bias_Calc, REFINED_Im_Gen

##########################################
#                                        #                                              
#                                        #                               
#               Data Cleaning            #   
#                                        #   
##########################################

cell_lines = ["HCC_2998","MDA_MB_435", "SNB_78", "NCI_ADR_RES","DU_145", "786_0", "A498","A549_ATCC","ACHN","BT_549","CAKI_1","DLD_1","DMS_114","DMS_273","CCRF_CEM","COLO_205","EKVX"]
#cell_lines = ["HCC_2998"]
Results_Dic = {}
SAVE_PATH = "C:\\Users\\obazgir\\Desktop\\REFINED project\\Volumetric REFINED\\NCI_Regression\\"
#%%
for SEL_CEL in cell_lines:
	# Loading the the drug responses and their IDs (NSC)
    DF = pd.read_csv("C:\\Users\\obazgir\\Desktop\\CMDS_IMAGES_NEW\\NCI60_GI50_normalized_April.csv")
    FilteredDF = DF.loc[DF.CELL==SEL_CEL]											# Pulling out the selected cell line responses
    FilteredDF = FilteredDF.drop_duplicates(['NSC'])                                # Dropping out the duplicates


    Feat_DF = pd.read_csv("C:\\Users\\obazgir\\Desktop\\CMDS_IMAGES_NEW\\normalized_padel_feats_NCI60_672.csv")	# Load the drug descriptors of the drugs applied on the selected cell line 
    Cell_Features = Feat_DF[Feat_DF.NSC.isin(FilteredDF.NSC)]
    TargetDF = FilteredDF[FilteredDF.NSC.isin(Cell_Features.NSC)]
    
    Y = np.array(TargetDF.NORMLOG50)
    # Features
    X = Cell_Features.values
    X = X[:,2:]
    # fix random seed for reproducibility
    seed = 10
    np.random.seed(seed)
    # split training, validation and test sets based on each sample NSC ID
    NSC_All = np.array(TargetDF['NSC'],dtype = int)
    Train_Ind, Rest_Ind, Y_Train, Y_Rest = train_test_split(NSC_All, Y, test_size= 0.2, random_state=seed)
    Validation_Ind, Test_Ind, Y_Validation, Y_Test = train_test_split(Rest_Ind, Y_Rest, test_size= 0.5, random_state=seed)
    # Sort the NSCs
    Train_Ind = np.sort(Train_Ind)
    Validation_Ind = np.sort(Validation_Ind)
    Test_Ind = np.sort(Test_Ind)
    # Extracting the drug descriptors of each set based on their associated NSCs
    X_Train_Raw = Cell_Features[Cell_Features.NSC.isin(Train_Ind)]
    X_Validation_Raw = Cell_Features[Cell_Features.NSC.isin(Validation_Ind)]
    X_Test_Raw = Cell_Features[Cell_Features.NSC.isin(Test_Ind)]
    
    Y_Train = TargetDF[TargetDF.NSC.isin(Train_Ind)];  Y_Train = np.array(Y_Train['NORMLOG50']) 
    Y_Validation = TargetDF[TargetDF.NSC.isin(Validation_Ind)];  Y_Validation = np.array(Y_Validation['NORMLOG50']) 
    Y_Test = TargetDF[TargetDF.NSC.isin(Test_Ind)];  Y_Test = np.array(Y_Test['NORMLOG50']) 
    
    X_Dummy = X_Train_Raw.values;     X_Train = X_Dummy[:,2:]
    X_Dummy = X_Validation_Raw.values;     X_Validation = X_Dummy[:,2:]
    X_Dummy = X_Test_Raw.values;      X_Test = X_Dummy[:,2:]
    
    Y_Val_Save = np.zeros(((len(Y_Validation)),6))
    Y_Val_Save[:,0] = Y_Validation
    Y_Test_Save = np.zeros(((len(Y_Test)),6))
    Y_Test_Save[:,0] = Y_Test
    #%% REFINED coordinates
    # LE
    import math
    with open('C:\\Users\\obazgir\\Desktop\\REFINED project\\Volumetric REFINED\\theMapping_Init_LE.pickle','rb') as file:
        gene_names_LE,coords_LE,map_in_int_LE = pickle.load(file)
    # LLE
    with open('C:\\Users\\obazgir\\Desktop\\REFINED project\\Volumetric REFINED\\theMapping_Init_LLE.pickle','rb') as file:
        gene_names_LLE,coords_LLE,map_in_int_LLE = pickle.load(file)
    # ISOMAP
    with open('C:\\Users\\obazgir\\Desktop\\REFINED project\\Volumetric REFINED\\theMapping_Init_ISO.pickle','rb') as file:
        gene_names_ISO,coords_ISO,map_in_int_ISO = pickle.load(file)
    # MDS
    with open('C:\\Users\\obazgir\\Desktop\\REFINED project\\Volumetric REFINED\\theMapping_REFINED_5.pickle','rb') as file:
        gene_names_MDS,coords_MDS,map_in_int_MDS = pickle.load(file)
          
    #%% importing tensorflow    
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.callbacks import EarlyStopping
    Model_Names = ["MDS","LE","LLE","ISO","VOLUMETRIC"]
    Results_Data = np.zeros((5,4))
    nn = 26  
    cnt = 0                                                               	# Image size = sqrt(#features (drug descriptors))		
    for modell in Model_Names:
        
        # Convert data into images using the coordinates generated by REFINED 
        if modell == "MDS":
            X_Train_REFINED = REFINED_Im_Gen(X_Train,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)
            X_Val_REFINED = REFINED_Im_Gen(X_Validation,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)
            X_Test_REFINED = REFINED_Im_Gen(X_Test,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)
        elif modell == "LE":
            X_Train_REFINED = REFINED_Im_Gen(X_Train,nn, map_in_int_LE, gene_names_LE,coords_LE)
            X_Val_REFINED = REFINED_Im_Gen(X_Validation,nn, map_in_int_LE, gene_names_LE,coords_LE)
            X_Test_REFINED = REFINED_Im_Gen(X_Test,nn, map_in_int_LE, gene_names_LE,coords_LE)
        elif modell == "LLE":
            X_Train_REFINED = REFINED_Im_Gen(X_Train,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)
            X_Val_REFINED = REFINED_Im_Gen(X_Validation,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)
            X_Test_REFINED = REFINED_Im_Gen(X_Test,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)
        elif modell == "ISO":
            X_Train_REFINED = REFINED_Im_Gen(X_Train,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)
            X_Val_REFINED = REFINED_Im_Gen(X_Validation,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)
            X_Test_REFINED = REFINED_Im_Gen(X_Test,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)																																						
        elif modell == "VOLUMETRIC":
            X_Train_REFINED = np.zeros((X_Train.shape[0],nn**2,4))
            X_Val_REFINED = np.zeros((X_Validation.shape[0],nn**2,4))
            X_Test_REFINED = np.zeros((X_Test.shape[0],nn**2,4))
            
            Temp_Train = REFINED_Im_Gen(X_Train,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)
            X_Train_REFINED[:,:,0] = REFINED_Im_Gen(X_Train,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)
            X_Val_REFINED[:,:,0] = REFINED_Im_Gen(X_Validation,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)
            X_Test_REFINED[:,:,0] = REFINED_Im_Gen(X_Test,nn, map_in_int_ISO, gene_names_ISO,coords_ISO)	

            X_Train_REFINED[:,:,1] = REFINED_Im_Gen(X_Train,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)
            X_Val_REFINED[:,:,1] = REFINED_Im_Gen(X_Validation,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)
            X_Test_REFINED[:,:,1] = REFINED_Im_Gen(X_Test,nn, map_in_int_MDS, gene_names_MDS,coords_MDS)

            X_Train_REFINED[:,:,2] = REFINED_Im_Gen(X_Train,nn, map_in_int_LE, gene_names_LE,coords_LE)
            X_Val_REFINED[:,:,2] = REFINED_Im_Gen(X_Validation,nn, map_in_int_LE, gene_names_LE,coords_LE)
            X_Test_REFINED[:,:,2] = REFINED_Im_Gen(X_Test,nn, map_in_int_LE, gene_names_LE,coords_LE)

            X_Train_REFINED[:,:,3] = REFINED_Im_Gen(X_Train,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)
            X_Val_REFINED[:,:,3] = REFINED_Im_Gen(X_Validation,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)
            X_Test_REFINED[:,:,3] = REFINED_Im_Gen(X_Test,nn, map_in_int_LLE, gene_names_LLE,coords_LLE)


        #%% Defining the CNN Model
        
        sz = X_Train_REFINED.shape
        Width = int(math.sqrt(sz[1]))
        Height = int(math.sqrt(sz[1]))
        if modell != "VOLUMETRIC":
            
            CNN_Train = X_Train_REFINED.reshape(-1,Width,Height,1)
            CNN_Val = X_Val_REFINED.reshape(-1,Width,Height,1)
            CNN_Test = X_Test_REFINED.reshape(-1,Width,Height,1)
        else:
            CNN_Train = X_Train_REFINED.reshape(-1,Width,Height,4,1)
            CNN_Val = X_Val_REFINED.reshape(-1,Width,Height,4,1)
            CNN_Test = X_Test_REFINED.reshape(-1,Width,Height,4,1)
    
        def CNN_model(Width,Height,modell):
            nb_filters = 64
            nb_conv = 7
            if modell == "VOLUMETRIC":
                model = models.Sequential()
                # Convlolutional layers
                model.add(layers.Conv3D(nb_filters, (nb_conv, nb_conv,1),padding='valid',strides=2,dilation_rate=1,input_shape=(Width, Height,4,1)))
                model.add(layers.BatchNormalization())
                model.add(layers.Activation('relu'))
                model.add(layers.Conv3D(nb_filters, (nb_conv, nb_conv,1),padding='valid',strides=2,dilation_rate=1))
                model.add(layers.BatchNormalization())
                model.add(layers.Activation('relu'))
            else:
                model = models.Sequential()
                # Convlolutional layers
                model.add(layers.Conv2D(nb_filters, (nb_conv, nb_conv),padding='valid',strides=2,dilation_rate=1,input_shape=(Width, Height,1)))
                model.add(layers.BatchNormalization())
                model.add(layers.Activation('relu'))
                model.add(layers.Conv2D(nb_filters, (nb_conv, nb_conv),padding='valid',strides=2,dilation_rate=1))
                model.add(layers.BatchNormalization())
                model.add(layers.Activation('relu'))
            
            model.add(layers.Flatten())
            # Dense layers
            model.add(layers.Dense(256))
            model.add(layers.BatchNormalization())
            model.add(layers.Activation('relu'))
            
            model.add(layers.Dense(64))
            model.add(layers.BatchNormalization())
            model.add(layers.Activation('relu'))
            model.add(layers.Dropout(1-0.7))
            
            model.add(layers.Dense(1))
            
            if modell == "VOLUMETRIC":
                initial_learning_rate = 0.0001
                lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
                    initial_learning_rate,
                    decay_steps=100000,
                    decay_rate=0.96,
                    staircase=True)
                model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=lr_schedule),
                loss='mse',
                metrics=['mse'])
            else:
                opt = tf.keras.optimizers.Adam(lr=0.0001)
                model.compile(loss='mse', optimizer = opt)
            #opt = tf.keras.optimizers.Adam(lr=0.0001)
            
            #model.compile(loss='mse', optimizer = opt)
            return model
        # Training the CNN Model
        model = CNN_model(Width,Height,modell)
        ES = EarlyStopping(monitor='val_loss', mode='min', verbose=0, patience=30)
        CNN_History = model.fit(CNN_Train, Y_Train, batch_size= 128, epochs = 250, verbose=0, validation_data=(CNN_Val, Y_Validation), callbacks = [ES])
        Y_Val_Pred_CNN = model.predict(CNN_Val, batch_size= 128, verbose=1)
        Y_Pred_CNN = model.predict(CNN_Test, batch_size= 128, verbose=1)
        
        Y_Val_Save[:,cnt+1] = Y_Val_Pred_CNN.reshape(-1)
        Y_Test_Save[:,cnt+1] = Y_Pred_CNN.reshape(-1)
        
        #print(model.summary())
        # Plot the Model
#        plt.plot(CNN_History.history['loss'], label='train')
#        plt.plot(CNN_History.history['val_loss'], label='Validation')
#        plt.legend()
#        plt.show()
        
        # Measuring the REFINED-CNN performance (NRMSE, R2, PCC, Bias)
        CNN_NRMSE, CNN_R2 = NRMSE(Y_Test, Y_Pred_CNN)
        print(CNN_NRMSE,"NRMSE of "+ modell + SEL_CEL)
        print(CNN_R2,"R2 of " + modell + SEL_CEL)
        Y_Test = np.reshape(Y_Test, (Y_Pred_CNN.shape))
        CNN_ER = Y_Test - Y_Pred_CNN
        CNN_PCC, p_value = pearsonr(Y_Test, Y_Pred_CNN)
        
        print(CNN_PCC,"PCC of " + modell+ SEL_CEL)
        Y_Validation = Y_Validation.reshape(len(Y_Validation),1)
        Y_Test = Y_Test.reshape(len(Y_Test),1)
        Bias = Bias_Calc(Y_Test, Y_Pred_CNN)
        
        Results_Data[cnt,:] = [CNN_NRMSE,CNN_PCC,CNN_R2,Bias]
        cnt +=1
    Results = pd.DataFrame(data = Results_Data , columns = ["NRMSE","PCC","R2","Bias"], index = Model_Names)
    Y_Val_Save_PD = pd.DataFrame(data = Y_Val_Save , columns = ["Y_Val","MDS","LE","LLE","ISO","VOL"])
    Y_Test_Save_PD = pd.DataFrame(data = Y_Test_Save , columns = ["Y_Val","MDS","LE","LLE","ISO","VOL"])
    
    Y_Val_Save_PD.to_csv(SAVE_PATH + SEL_CEL + "VAL.csv")
    Y_Test_Save_PD.to_csv(SAVE_PATH + SEL_CEL + "TEST.csv")
    Results_Dic[SEL_CEL] = Results
    
print(Results_Dic)

with open(SAVE_PATH+'Results_Dic.csv', 'w') as f:[f.write('{0},{1}\n'.format(key, value)) for key, value in Results_Dic.items()]
