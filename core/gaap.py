# -*- coding:utf-8 -*-
import numpy as np
import core.tbl_manage as tm
import core.pricing as pc
import core.stat as stat
#from peewee import *
from functools import reduce

class Gaap(object):
    def __init__(self, plan_id):
        self.plan_id = plan_id
        self.pricing = pc.PricingOd(plan_id)
        self.stat = stat.Stat(plan_id)
    IssAge = 30
    sa = 1000
    sex = 0
    payterm = 10
    insterm = 75
    load_tbl_name = "Loading_10513002"
    IntRate = 0.035
    method = "FPT"

    def apv_mp_age(self):
        """
        :return: model points对应的age列 
        :rtype: np.ndarray
        """
        if self.insterm == "105@":
            mp_age = np.array(range(self.IssAge, 106, 1), dtype='int32')
        else:
            mp_age = np.array(range(self.IssAge, self.IssAge + self.insterm, 1), dtype='int32')
        return mp_age

    def apv_mp_polyr(self):
        """

        :return: model points对应的保单年度列
        :rtype: np.ndarray
        """
        polyr = np.arange(len(self.apv_mp_age()), dtype='int32') + 1
        return polyr


    def pv_cf(self):
        pv_cf = self.pv_cf_prem() + self.pv_cf_exp() + pr
