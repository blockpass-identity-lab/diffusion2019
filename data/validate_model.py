import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import sys
import traceback


# prep
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from sklearn.datasets import make_classification
from sklearn.preprocessing import binarize, LabelEncoder, MinMaxScaler
from sklearn import metrics

# models
from torch import nn
from torch import optim
from torch.autograd import Variable
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from demo.runners.support.utils import log_msg




async def validate_model(model_path):
    log_msg("COORDINATOR IS CLEANING THE VALIDATION SET")

    #Read in Data
    train_df = pd.read_csv('data/data.csv')

    log_msg("COORDINATOR DATA", train_df)

    ########## START DATA CLEANING ###############
    #Let’s get rid of the variables "Timestamp",“comments”, “state” just to make our lives easier.
    train_df = train_df.drop(['comments'], axis= 1)
    train_df = train_df.drop(['state'], axis= 1)
    train_df = train_df.drop(['Timestamp'], axis= 1)

    # Assign default values for each data type
    defaultInt = 0
    defaultString = 'NaN'
    defaultFloat = 0.0

    # Create lists by data tpe
    intFeatures = ['Age']
    stringFeatures = ['Gender', 'Country', 'self_employed', 'family_history', 'treatment', 'work_interfere',
                     'no_employees', 'remote_work', 'tech_company', 'anonymity', 'leave', 'mental_health_consequence',
                     'phys_health_consequence', 'coworkers', 'supervisor', 'mental_health_interview', 'phys_health_interview',
                     'mental_vs_physical', 'obs_consequence', 'benefits', 'care_options', 'wellness_program',
                     'seek_help']
    floatFeatures = []

    # Clean the NaN's
    for feature in train_df:
        if feature in intFeatures:
            train_df[feature] = train_df[feature].fillna(defaultInt)
        elif feature in stringFeatures:
            train_df[feature] = train_df[feature].fillna(defaultString)
        elif feature in floatFeatures:
            train_df[feature] = train_df[feature].fillna(defaultFloat)
        else:
            log_msg('Error: Feature %s not recognized.' % feature)

    #clean 'Gender'
    #Slower case all columm's elements
    gender = train_df['Gender'].str.lower()
    #log_msg(gender)

    #Select unique elements
    gender = train_df['Gender'].unique()

    #Made gender groups
    male_str = ["male", "m", "male-ish", "maile", "mal", "male (cis)", "make", "male ", "man","msle", "mail", "malr","cis man", "Cis Male", "cis male"]
    trans_str = ["trans-female", "something kinda male?", "queer/she/they", "non-binary","nah", "all", "enby", "fluid", "genderqueer", "androgyne", "agender", "male leaning androgynous", "guy (-ish) ^_^", "trans woman", "neuter", "female (trans)", "queer", "ostensibly male, unsure what that really means"]
    female_str = ["cis female", "f", "female", "woman",  "femake", "female ","cis-female/femme", "female (cis)", "femail"]

    for (row, col) in train_df.iterrows():

        if str.lower(col.Gender) in male_str:
            train_df['Gender'].replace(to_replace=col.Gender, value='male', inplace=True)

        if str.lower(col.Gender) in female_str:
            train_df['Gender'].replace(to_replace=col.Gender, value='female', inplace=True)

        if str.lower(col.Gender) in trans_str:
            train_df['Gender'].replace(to_replace=col.Gender, value='trans', inplace=True)

    #Get rid of bullshit
    stk_list = ['A little about you', 'p']
    train_df = train_df[~train_df['Gender'].isin(stk_list)]

    #complete missing age with mean
    train_df['Age'].fillna(train_df['Age'].median(), inplace = True)

    # Fill with media() values < 18 and > 120
    s = pd.Series(train_df['Age'])
    s[s<18] = train_df['Age'].median()
    train_df['Age'] = s
    s = pd.Series(train_df['Age'])
    s[s>120] = train_df['Age'].median()
    train_df['Age'] = s

    #Ranges of Age
    train_df['age_range'] = pd.cut(train_df['Age'], [0,20,30,65,100], labels=["0-20", "21-30", "31-65", "66-100"], include_lowest=True)

    #There are only 0.20% of self work_interfere so let's change NaN to "Don't know
    #Replace "NaN" string from defaultString

    train_df['work_interfere'] = train_df['work_interfere'].replace([defaultString], 'Don\'t know' )

    #Encoding data
    labelDict = {}
    for feature in train_df:
        le = preprocessing.LabelEncoder()
        le.fit(train_df[feature])
        le_name_mapping = dict(zip(le.classes_, le.transform(le.classes_)))
        train_df[feature] = le.transform(train_df[feature])
        # Get labels
        labelKey = 'label_' + feature
        labelValue = [*le_name_mapping]
        labelDict[labelKey] =labelValue

    #Get rid of 'Country'
    train_df = train_df.drop(['Country'], axis= 1)

    # Scaling Age
    scaler = MinMaxScaler()
    train_df['Age'] = scaler.fit_transform(train_df[['Age']])

    # define X and y
    feature_cols = ['Age', 'Gender', 'family_history', 'benefits', 'care_options', 'anonymity', 'leave', 'work_interfere']
    X = train_df[feature_cols]
    y = train_df.treatment

    # split X and y into training and testing sets
    X_test, y_test = X, y

    # Transform pandas dataframe to torch tensor for DL

    x_test_data = torch.from_numpy(X_test.values)
    x_test_data = x_test_data.float()

    y_test_data = []
    for data in y_test.values:
        y_test_data.append([data])
    y_test_data = torch.tensor(y_test_data).float()

    log_msg("VALIDATION SET HAS BEEN CLEANED")

    ########## END DATA CLEANING ###############


    log_msg(model_path)
    # Pull in model

    model = torch.load(model_path)

    log_msg("HOSPITAL MODEL LOADED")
    log_msg("\nPRINTING PARAMETERS:\n\n")


    log_msg(model)

    log_msg('\n')

    for name, param in model.named_parameters():
        if param.requires_grad:
            log_msg(name, param.data)

    # Validation Logic
    log_msg("\n\n\nHOSPITAL IS VALIDATING")

    #BINARIZE PREDICTION FOR CONFUSION MATRIX

    pred = []

    for data in  model(x_test_data):
        if data > .5:
            pred.append(1)
        else:
            pred.append(0)


    confusion = metrics.confusion_matrix(pred, y_test_data)

    log_msg("Model loss on validation set: ", (model(x_test_data) - y_test_data).sum())
    log_msg("Confusion Matrix:\n                Actual_True, Actual_False \n Predicted_True    ",confusion[1][1],"   |     ",confusion[1][0],"    \n Predicted_False   ",confusion[0][1],"     |      ",confusion[0][0],"    \n")

    return True
