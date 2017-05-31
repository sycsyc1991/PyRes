# -*- coding:utf-8 -*-
import numpy as np
import core.tbl_manage as tm
import core.pricing as pc
import core.stat as stat
#from peewee import *
from functools import reduce

class Gaap(object):
    def __init__(self, plan_id, time_scale):
        self.plan_id = plan_id
        self.pricing = pc.PricingOd(plan_id)
        self.stat = stat.Stat(plan_id)
        self.time_scale = time_scale
    IssAge = 30
    sa = 1000
    SA = 1000000
    sex = 0
    payterm = 10
    insterm = 76
    load_tbl_name = "Loading_10513002"
    lapse_tbl_name = "Lapse_10513002"
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
        if self.time_scale is "MONTH":
            mp_age = np.repeat(mp_age, 12)
        else:
            pass
        return mp_age

    def apv_mp_polmth(self):
        """
        
        :return: 
        """
        if self.time_scale is "MONTH":
            polmth = np.arange(len(self.apv_mp_age()), dtype='int32') + 1
        else:
            polmth = np.ones(len(self.apv_mp_age()), dtype='int32')
        return polmth

    def apv_mp_mth(self):
        return 0

    def apv_mp_polyr(self):
        """

        :return: model points对应的保单年度列
        :rtype: np.ndarray
        """
        polyr = self.apv_mp_age() - self.apv_mp_age()[0] + 1
        return polyr

    def ben_list(self):
        return self.pricing.ben_list()

    def adj_qx_list(self, sex, ben):
        """

        :param sex: 被保险人性别
        :param ben: 调整发生率的责任
        :return: qx
        :rtype: np.ndarray
        """
        qx = self.pricing.get_qx_list(sex, ben.get_qx_tbl())
        if ben.BEN_TYPE == "death":
            qx = qx * (1 - self.pricing.get_qx_list(self.sex, tm.ReadTable.get_mort_table("K_2000_1.csv")).values)
        return qx

    @staticmethod
    def ytom(rate):
        rate = 1 - (1-rate) ** (1/12)
        return rate

    def mp_qx_ben(self, ben):
        """

        :param ben: 责任列表
        :return: mp对应的ben_list的发生率 
        """
        try:
            qx = [self.adj_qx_list(self.sex, x) for x in ben]
        except TypeError:
            qx = self.adj_qx_list(self.sex, ben)
        y2m = np.frompyfunc(lambda x: self.ytom(x), 1, 1)
        if self.time_scale is "MONTH":
            qx = np.repeat(qx, 12).values
            qx = y2m(qx)
        else:
            qx = qx
        return qx

    def mp_qx_ben_list(self,ben):
        """
        
        :param ben: 
        :return: 
        """
        try:
            qx = [self.mp_qx_ben(x) for x in ben]
        except TypeError:
            qx = self.mp_qx_ben(ben)
        return qx

    @staticmethod
    def get_lapse_list(payterm, tbl_name):
        tbl_name = tbl_name + ".csv"
        # tbl_name_firstyear = tbl_name + "_Firstyear.csv"
        tbl = tm.ReadTable.get_lapse_table(tbl_name)
        lapse_list = tbl[str(payterm)]
        return lapse_list
    # TODO lapse list 归类

    def mp_lapse(self):
        """

        :return: lapse列 
        :rtype: np.ndarray
        """
        lapse = self.get_lapse_list(self.payterm, self.lapse_tbl_name).values
        lapse[np.isnan(lapse)] = 0
        lap = lapse[:len(self.pricing.apv_mp_age())]
        y2m = np.frompyfunc(lambda x: self.ytom(x), 1, 1)
        if self.time_scale is "MONTH":
            lap = np.repeat(lap, 12)
            lap = y2m(lap)
        else:
            lap = lap
        return lap

    def mp_lx_cal(self):
        """

        :return: mp对应的年末Inforce
        """
        if [x for x in self.ben_list() if x.BEN_TYPE == "death"].__len__() != 1:
            raise NotImplementedError("death benifit number error")
        # db部分处理
        qx = self.mp_qx_ben_list(self.ben_list())
        lap = self.mp_lapse()
        lx = (1 - reduce(lambda x, y: x + y, qx))*(1 - lap)
        lx = lx.cumprod()
        return lx

    def mp_lx_eop(self):
        return self.mp_lx_cal()

    def mp_lx_bop(self):
        lx = np.roll(self.mp_lx_eop(), 1)
        lx[0] = 1
        return lx

    def mp_prem(self):
        prem = np.zeros(len(self.apv_mp_age()), dtype='int32')
        if self.time_scale is "MONTH":
            prem[np.arange(self.payterm) * 12] = 1
        else:
            prem[:self.payterm] = 1
        prem = prem * self.SA / a.pricing.gp()
        prem = prem * a.mp_lx_bop()
        return prem

    def mp_ben(self):
        """
        
        :return:未贴现 
        """
        ben = self.pricing.b
        ben = self.mp_qx_ben_list(self.ben_list())
        return qx

    def mp_ben_fix(self, ben):
        ben_fix = self.pricing.mp_ben_fix(ben)
        if self.time_scale is "MONTH":
            ben_fix = np.repeat(ben_fix, 12)
        return self.mp_qx_ben_list(ben) * self.mp_lx_bop() * ben_fix

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
    # ben的总和


if __name__ == '__main__':
    a = Gaap(10513002, "MONTH")
    b = a.mp_ben_fix(a.ben_list()[1])
    # print(a.mp_qx_ben_list(a.ben_list()))
    print(b)
    print(len(b))