from simanneal import Annealer
import numpy as np
import pandas as pd
import json

def min_max_norm(df):
    return (df-df.min()) / (df.max()-df.min())


def mean_norm(df):
    return (df-df.mean()) / df.std()

def df_to_json(df, file_path):
    """
    Saves pass
    :param df: df to be saved as json
    :param file_path: path, where new file is to be created to save df as json. (including filename)
    :return:
    """

    file = open(file_path, "x")
    json.dump(df.to_json(), file)
    file.close()

def read_json_df(file_path):
    file = open(file_path, 'rb')
    df = pd.DataFrame(json.load(file))
    file.close()
    return df

