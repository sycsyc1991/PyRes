import os
import pandas as pd


class ReadTable(object):

    FILE_PATH = os.path.realpath(__file__)
    BASE_DIRECTORY = os.path.split(FILE_PATH)[0]
    BASE_DIRECTORY = os.path.split(BASE_DIRECTORY)[0]
    PLAN_DIRECTORY = os.path.join(BASE_DIRECTORY, "plan")
    MORT_TABLE_DIRECTORY = os.path.join(BASE_DIRECTORY, "table")
    SA_TABLE_DIRECTORY = os.path.join(BASE_DIRECTORY, "sa")
    LOADING_TABLE_DIRECTORY = os.path.join(BASE_DIRECTORY, "loading")

    @classmethod
    def get_plan_table(cls):
        tbl = pd.read_csv(os.path.join(cls.PLAN_DIRECTORY, "list_plan_benifit.csv"))
        return tbl

    @classmethod
    def get_ben_table(cls):
        tbl = pd.read_csv(os.path.join(cls.PLAN_DIRECTORY, "list_benifit.csv"))
        return tbl

    @classmethod
    def get_mort_table(cls, tbl_name):
        tbl = pd.read_csv(os.path.join(cls.MORT_TABLE_DIRECTORY, tbl_name))
        return tbl

    @classmethod
    def get_load_table(cls, tbl_name):
        tbl = pd.read_csv(os.path.join(cls.LOADING_TABLE_DIRECTORY, tbl_name))
        return tbl
