# -*- coding:utf-8 -*-
import numpy as np
import tbl_manage as tm
import pricing as pc
import exceptions
from peewee import *
from playhouse import postgres_ext as pge
import os

class Stat(object):
    def __init__(self, plan_id):
        self.plan_id = plan_id
        self.pricing = pc.PricingOd(plan_id)
    IssAge = 30
    sa = 1000
    sex = 0
    payterm = 10
    insterm = 75
    load_tbl_name = "Loading_10513002"
    IntRate = 0.035
    method = "FPT"

    def apv_mp_age(self):
        return self.pricing.apv_mp_age()
    # 生成model points对应的age列

    def apv_mp_polyr(self):
        return self.pricing.apv_mp_polyr()
    # 生成model points对应的保单难度列

    def ben_list(self):
        return self.pricing.ben_list()

    def mp_lx_init(self):
        lx = np.ones(len(self.pricing.apv_mp_age()))
        return lx

    def mp_lx_cal(self):
        if filter(lambda x: x.BEN_TYPE == "death", self.ben_list()).__len__() != 1:
            raise exceptions.NotImplementedError("death benifit number error")
        # db部分处理
        ben_death = filter(lambda x: x.BEN_TYPE == "death", self.ben_list())[0]
        ben_ci = filter(lambda x: x.BEN_TYPE == "ci", self.ben_list())[0]
        lx = self.mp_lx_init()
        qx = self.mp_qx_ben(ben_death)
        cix = self.mp_qx_ben(ben_ci)
        for i in self.pricing.apv_mp_polyr()[:-1] - 1:
            lx[i + 1] = reduce(self.pricing.lx_cal, (lx[i], lx[i] * qx[i], lx[i] * cix[i]))
        return lx

    def mp_qx_ben(self, ben):
        qx = self.pricing.get_qx_list(self.sex, ben.get_qx_tbl()).values
        if ben.BEN_TYPE == "death":
            qx = qx * (1 - self.pricing.get_qx_list(self.sex, tm.ReadTable.get_mort_table("K_2000_1.csv")).values)
        return qx
        # 读取ben对应的model points的qx

    def mp_dx(self, phase="moy"):
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_cal() / (1 + self.IntRate) ** (self.pricing.apv_mp_polyr() - adj[phase])
        return dx
    # Dx calculate

    def mp_cx_ben(self, ben, phase="moy"):
        cx = self.mp_dx(phase) * self.mp_qx_ben(ben)
        # 与换算函数不同，减少了年末给付的贴现
        return cx
    # Cx calculate

    def mp_ben_fix(self, ben):
        return self.mp_cx_ben(ben) * self.pricing.mp_ben_fix(ben)

    def apv_ben_fix_list(self):
        ben_out_list = map(self.mp_ben_fix, self.ben_list())
        return ben_out_list

    def mp_ben_prem(self, ben):
        return self.mp_cx_ben(ben) * self.pricing.mp_ben_prem(ben)
    # 单个ben（prem类型）的apv计算

    def apv_ben_prem_list(self):
        return map(self.mp_ben_prem, self.ben_list())
    # ben list（prem类型）的apv

    def apv_ben_total(self):
        return reduce(lambda x, y: x+y, self.apv_ben_fix_list()) + (self.pricing.gp() * reduce(lambda x, y: x+y, self.apv_ben_prem_list()))
    # ben的apv总和

    def mp_p(self):
        prem = np.zeros(len(self.apv_mp_age()), dtype='int32')
        prem[:self.payterm] = 1
        gross_p = prem * self.mp_dx("boy")
        return gross_p
    # 贴现使用年初

    def trnp(self):
        trnp = np.zeros(len(self.apv_mp_polyr()))
        if self.method == "FPT":
            trnp[0] = self.apv_ben_total()[0]
            trnp[1:self.payterm] = (sum(self.apv_ben_total()) - trnp[0]) / (sum(self.mp_p()) - 1)
        return trnp

    # def reserve(self):
    #     res = np.zeros(len(self.apv_mp_polyr()))
    #     for i in self.apv_mp_polyr()[len(self.apv_mp_polyr())-2::-1]:
    #         res[i-1] = (res[i] * self.mp_dx()[i] + self.apv_ben_total()[i-1] - self.mp_dx()[i-1] * self.trnp("FPT")[i-1]) / self.mp_dx()[i-1]
    #     return res

    def stat(self):
        res = self.apv_ben_total() - self.trnp() * self.mp_dx("boy")
        res = np.roll(res[::-1].cumsum()[::-1] / self.mp_dx("boy"), -1)
        res[0] = 0
        return res

    pass

a = Stat(10513002)
print a.mp_dx("boy")
print a.stat()