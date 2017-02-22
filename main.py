# coding: utf-8

# Captain obvious
import numpy as np
import pandas as pd

# feature preprocessing
from sklearn.preprocessing import RobustScaler,StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.feature_extraction import FeatureHasher
from sklearn.metrics import make_scorer


#Dimensionality reduction
from sklearn.decomposition import TruncatedSVD, NMF

# feature selection
# from sklearn.feature_selection import SelectFromModel, RFECV
# from sklearn.model_selection import StratifiedKFold

# Custom helper functions
from src.star_command import feat_extraction_pipe
from main_output import output
from main_train import training_step
from src.preprocessing import preprocessing
from src.metrics import mlogloss

# Mesure time
from timeit import default_timer as timer

# Set random seed for reproducibility
np.random.seed(1337)

# Start timer
start_time = timer()

# # Import data
df_train = pd.read_json(open("./data/train.json", "r"))
df_test = pd.read_json(open("./data/test.json", "r"))

print('Input training data has shape: ',df_train.shape)
print('Input test data has shape:     ',df_test.shape)

X = df_train
X_test = df_test
y = df_train['interest_level']
idx_test = df_test['listing_id']

###### TODO ###########
# Bucket nombre de chambres et de bathrooms
# Retirer numéro de rue - DONE ?
# Imputer les rues sans géoloc
# Quartier (centre le plus proche)
# Distance par rapport au centre
# Clusteriser la latitude/longitude
# manager skill (2*high + medium)
# TFIDF - Naive Bayes and/or SVM

#######################

# # Command Center

from src.transformers_numeric import tr_numphot, tr_numfeat, tr_numdescwords
from src.transformers_time import tr_datetime
from src.transformers_debug import tr_dumpcsv
from src.transformers_nlp_tfidf import tr_tfidf_lsa_lgb
from src.transformers_appart_features import tr_tfidf_features

# Feature extraction - sequence of transformations
tr_pipeline = feat_extraction_pipe(
    tr_numphot,
    tr_numfeat,
    tr_numdescwords,
    tr_datetime,
    tr_tfidf_lsa_lgb,
    tr_tfidf_features
    #tr_dumpcsv
)

mlog_score = make_scorer(mlogloss, greater_is_better=False,needs_proba=True)

# Feature selection - features to keep
select_feat = [
    ("bathrooms",None),
    (["bedrooms"],None),
    (["latitude"],None),
    (["longitude"],None),
    (["price"],None),
    (["NumDescWords"],None),
    (["NumFeat"],None),
    (["NumPhotos"],None),
    ("Created_Year",None), #Every listing is 2016
    (["Created_Month"],None),
    (["Created_Day"],None),
    (["Created_Hour"],None),
    ('listing_id',None),
    #(["Created_DayOfWeek"],None),
    #("tfidf_high",None),
    #("tfidf_medium",None),
    #("tfidf_low",None),
    ("display_address",CountVectorizer()),
    ("street_address",CountVectorizer()),
    ("manager_id",CountVectorizer()),
    ("building_id",CountVectorizer()),
    ("joined_features", CountVectorizer( ngram_range=(1, 1),
                                        stop_words='english',
                                        max_features=200))
]

# Currently LightGBM core dumps on categorical data, deactivate in the transformer

################ Preprocessing #####################
cache_file = './cache.db'

x_trn, x_val, y_trn, y_val, X_test, labelencoder = preprocessing(
   X, X_test, y, tr_pipeline, select_feat, cache_file)

############ Train and Validate ####################
print("############ Final Classifier ######################")
clf, metric = training_step(x_trn, x_val, y_trn, y_val)

################## Predict #########################
output(X_test,idx_test,clf,labelencoder, metric)

end_time = timer()
print("################## Success #########################")
print("Elapsed time: %s" % (end_time - start_time))
