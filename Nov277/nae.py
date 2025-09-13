import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


class DataPreprocessor:
    def __init__(self, numerical_columns, categorical_columns):
        self.numerical_columns = numerical_columns
        self.categorical_columns = categorical_columns

        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', Pipeline([
                    ('imputer', SimpleImputer(strategy='median')),
                    ('scaler', StandardScaler())
                ]), numerical_columns),
                ('cat', Pipeline([
                    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
                    ('onehot', OneHotEncoder(handle_unknown='ignore'))
                ]), categorical_columns)
            ])

    def fit_transform(self, X):
        return self.preprocessor.fit_transform(X)


data = pd.DataFrame({
    'age': [25, np.nan, 35, 45],
    'income': [50000, 60000, np.nan, 75000],
    'city': ['New York', 'London', 'Paris', 'Tokyo']
})

preprocessor = DataPreprocessor(
    numerical_columns=['age', 'income'],
    categorical_columns=['city']
)
processed_data = preprocessor.fit_transform(data)
