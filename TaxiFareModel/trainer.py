# imports

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from TaxiFareModel.encoders import DistanceTransformer
from TaxiFareModel.encoders import TimeFeaturesEncoder
from sklearn.model_selection import train_test_split
from TaxiFareModel.utils import compute_rmse
from TaxiFareModel.data import clean_data, get_data
from memoized_property import memoized_property
import mlflow
from mlflow.tracking import MlflowClient


class Trainer():
    def __init__(self, X, y):
        """
            X: pandas DataFrame
            y: pandas Series
        """
        self.pipeline = None
        self.X = X
        self.y = y

    def set_pipeline(self):
        """defines the pipeline as a class attribute"""
        dist_pipe = Pipeline([('dist_trans', DistanceTransformer()),
                              ('stdscaler', StandardScaler())])

        time_pipe = Pipeline([('time_enc', TimeFeaturesEncoder('pickup_datetime')),
                          ('ohe', OneHotEncoder(handle_unknown='ignore'))])
        preproc_pipe = ColumnTransformer([('distance', dist_pipe, [
        "pickup_latitude", "pickup_longitude", 'dropoff_latitude',
        'dropoff_longitude'
        ]), ('time', time_pipe, ['pickup_datetime'])],
                                     remainder="drop")
        pipeline = Pipeline([('preproc', preproc_pipe),
                     ('linear_model', LinearRegression())])
        return pipeline

    def run(self):
        """set and train the pipeline"""
        self.pipeline=self.set_pipeline()
        self.pipeline.fit(self.X, self.y)
        return self.pipeline


    def evaluate(self, X_test, y_test):
        """evaluates the pipeline on df_test and return the RMSE"""
        self.pipeline=self.run()
        y_pred=self.pipeline.predict(X_test)
        rmse=compute_rmse(y_pred, y_test)
        return rmse

    MLFLOW_URI = "https://mlflow.lewagon.co/"
    EXPERIMENT_NAME='[FR][Paris][lilouconquet] TaxiFareModel 1.0'

    @memoized_property
    def mlflow_client(self):
        mlflow.set_tracking_uri(self.MLFLOW_URI)
        return MlflowClient()

    @memoized_property
    def mlflow_experiment_id(self):
        try:
            return self.mlflow_client.create_experiment(self.EXPERIMENT_NAME)
        except BaseException:
            return self.mlflow_client.get_experiment_by_name(self.EXPERIMENT_NAME).experiment_id

    @memoized_property
    def mlflow_run(self):
        return self.mlflow_client.create_run(self.mlflow_experiment_id)

    def mlflow_log_param(self, key, value):
        self.mlflow_client.log_param(self.mlflow_run.info.run_id, key, value)

    def mlflow_log_metric(self, key, value):
        self.mlflow_client.log_metric(self.mlflow_run.info.run_id, key, value)


if __name__ == "__main__":
    # get data
    df=get_data()
    # clean data
    df=clean_data(df)
    # set X and y
    y = df["fare_amount"]
    X = df.drop("fare_amount", axis=1)
    # hold out
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.15)
    # train
    trainer = Trainer(X_train, y_train)
    trainer.run()
    # evaluate
    rmse=trainer.evaluate(X_val, y_val)
    #
    trainer.mlflow_log_metric("rmse", rmse)
    trainer.mlflow_log_param("model", 'Linear Regression')
