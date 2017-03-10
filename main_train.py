# Classifier
import lightgbm as lgb
import xgboost as xgb
from src.metrics import mlogloss
import time
import numpy as np
from src.cross_val_xgb import cross_val_xgb
from src.cross_val_lgb import cross_val_lgb
from sklearn.model_selection import KFold, StratifiedKFold


def training_step(x_trn, x_val, y_trn, y_val, X_train, y_train):
    
    clf, y_pred, params, n_stop = _clf_xgb(x_trn, x_val, y_trn, y_val)
    #clf, y_pred, params, n_stop = _clf_lgb(x_trn, x_val, y_trn, y_val)

    # eval
    metric = mlogloss(y_val, y_pred)
    print('\n\nWe stopped at boosting round:  ', n_stop)
    print('The mlogloss of prediction is: ', metric)
    
    
    
    #lgb_train = lgb.Dataset(X_train, y_train)
    xgtrain = xgb.DMatrix(X_train, label=y_train)

    #Ideally cross val split should be done before feature engineering, and feature engineering + selection should be done separately for each splits so it better mimics out-of-sample predictions
    print('\n\nCross validating Stratified 7-fold... and retrieving best stopping round')
    
    #cv = lgb.cv(params, lgb_train, n_stop, nfold=5, seed=1337)
    #cv = xgb.cv(params, xgtrain, n_stop, nfold=5, seed=1337, early_stopping_rounds=50)
    
    
    #kf = KFold(n_splits=5, shuffle=True, random_state=1337) 
    kf = StratifiedKFold(n_splits=7, shuffle=True, random_state=1337)
    
    mean_round = cross_val_xgb(params, X_train, y_train, kf, metric)
    #mean_round = cross_val_lgb(params, X_train, y_train, kf, metric)
    
    #cv.to_csv('./out/'+time.strftime("%Y-%m-%d_%H%M-")+'-valid'+str(metric)+'-cv.csv')
    #print(cv)
    
    print('\n\nStart Training on the whole dataset...')
    #n_stop = np.int(mean_round * 1.1) #0.54874
    n_stop = np.int(mean_round) #0.54934 with XGBoost

    
    final_clf = xgb.train(params, xgtrain, n_stop)
    #final_clf = lgb.train(params, lgb_train, num_boost_round=n_stop)
    
    return final_clf, metric, n_stop


def _clf_lgb(x_trn, x_val, y_trn, y_val):
    # print('Type of data - check especially for categorical')
    # print(x_trn.dtypes)
    
    lgb_train = lgb.Dataset(x_trn, y_trn)
    lgb_eval = lgb.Dataset(x_val, y_val, reference=lgb_train)

    # specify your configurations as a dict
    params = {
        'task': 'train',
        'boosting_type': 'gbdt',
        'objective': 'multiclass',
        'num_class': 3,
        'metric': {'multi_logloss'},
        'learning_rate': 0.1,
        #'feature_fraction': 0.8,
        #'bagging_fraction': 0.8,
        'num_leaves': 32,
        #'bagging_freq': 3,
        'verbose': 0
    }

    print('Start Validation training on 80% of the dataset...')
    # train
    gbm = lgb.train(params,
                    lgb_train,
                    num_boost_round=2048,
                    valid_sets=lgb_eval,
                    early_stopping_rounds=50,
                    verbose_eval=True,
                    feature_name='auto')
    print('End trainind on 80% of the dataset...')
    
    print('Start validating prediction on 20% unseen data')
    # predict
    y_pred = gbm.predict(x_val, num_iteration=gbm.best_iteration)
    return gbm, y_pred, params, gbm.best_iteration

def _clf_xgb(x_trn, x_val, y_trn, y_val, feature_names=None, seed_val=0, num_rounds=4096):
    param = {}
    param['objective'] = 'multi:softprob'
    #param['eta'] = 0.02
    param['eta'] = 0.1
    #param['max_depth'] = 6
    param['max_depth'] = 4
    param['silent'] = 1
    param['num_class'] = 3
    param['eval_metric'] = "mlogloss"
    param['min_child_weight'] = 1
    param['subsample'] = 0.7
    param['colsample_bytree'] = 0.5
    param['seed'] = seed_val
    num_rounds = num_rounds

    plst = list(param.items())
    xgtrain = xgb.DMatrix(x_trn, label=y_trn)
    xgtest = xgb.DMatrix(x_val, label=y_val)
    
    print('Start Validation training on 80% of the dataset...')
    # train
    watchlist = [ (xgtest, 'test') ]
    model = xgb.train(plst, xgtrain, num_rounds, watchlist, early_stopping_rounds=100)
    print('End trainind on 80% of the dataset...')
    print('Start validating prediction on 20% unseen data')
    # predict
    y_pred = model.predict(xgtest, ntree_limit=model.best_ntree_limit)

    return model, y_pred, plst, model.best_ntree_limit