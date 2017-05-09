# -*- coding:utf-8 -*-
import numpy as np
import core.tbl_manage as tm
import core.pricing as pc
#from peewee import *
from functools import reduce

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

    def get_qx_list(self, sex, tbl):
        """

        :param sex: 
        :param tbl: 
        :return: 读取tbl中的model points对应的行
        """
        qx_list = tbl[tbl['age'].isin(self.apv_mp_age())]["male" if sex == 0 else "female"]
        return qx_list

    def adj_qx_list(self, sex, ben):
        """

        :param sex: 被保险人性别
        :param ben: 调整发生率的责任
        :return: qx
        :rtype: np.ndarray
        """
        qx = self.get_qx_list(sex, ben.get_qx_tbl())
        if ben.BEN_TYPE == "death":
            qx = qx * (1 - self.get_qx_list(self.sex, tm.ReadTable.get_mort_table("K_2000_1.csv")).values)
        return qx

    def mp_qx_ben_list(self, ben):
        """

        :param ben: 责任列表
        :return: mp对应的ben_list的发生率 
        """
        try:
            qx = [self.adj_qx_list(self.sex, x) for x in ben]
        except TypeError:
            qx = self.adj_qx_list(self.sex, ben)
        return qx

    def mp_lx_cal(self):
        """

        :return: mp对应的年末Inforce
        """
        if [x for x in self.ben_list() if x.BEN_TYPE == "death"].__len__() != 1:
            raise NotImplementedError("death benifit number error")
        # db部分处理
        qx = self.mp_qx_ben_list(self.ben_list())
        lx = 1 - reduce(lambda x, y: x + y, qx)
        lx = lx.cumprod()
        return lx

    def mp_lx_eop(self):
        return self.mp_lx_cal()

    def mp_lx_bop(self):
        lx = np.roll(self.mp_lx_eop(), 1)
        lx[0] = 1
        return lx

    def mp_dx(self, phase="moy"):
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_bop() / (1 + self.IntRate) ** (self.pricing.apv_mp_polyr() - adj[phase])
        return dx
    # Dx calculate

    def mp_cx_ben(self, ben, phase="moy"):
        cx = self.mp_dx(phase) * self.mp_qx_ben_list(ben)
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
        """
        计算修正净保费：
        （一）终身年金以外的人寿保险采用一年期完全修正方法
        :return: TRNP
        :rtype: pd.series
        """
        trnp = np.zeros(len(self.apv_mp_polyr()))
        if self.method == "FPT":
            trnp[0] = self.apv_ben_total().values[0]
            trnp[1:self.payterm] = (sum(self.apv_ben_total().values) - trnp[0]) / (sum(self.mp_p()) - 1)
        return trnp

    # def reserve(self):
    #     res = np.zeros(len(self.apv_mp_polyr()))
    #     for i in self.apv_mp_polyr()[len(self.apv_mp_polyr())-2::-1]:
    #         res[i-1] = (res[i] * self.mp_dx()[i] + self.apv_ben_total()[i-1] - self.mp_dx()[i-1] * self.trnp("FPT")[i-1]) / self.mp_dx()[i-1]
    #     return res

    def adj_rsv(self):
        """
        计算修正准备金
        :return: 修正Res列
        :rtype: np.ndarray
        """
        # TODO:需要注意首年的rsv是否为0
        res = self.apv_ben_total() - self.trnp() * self.mp_dx("boy")
        res = (res[::-1].cumsum()[::-1] / self.mp_dx("boy"))
        #res[0] = 0
        res = np.roll(res, -1)
        return res

    def prem_rsv(self):
        # TODO: 4位小数有差
        res = np.fmax(self.trnp() - self.pricing.gp(), 0) * self.mp_p()[::-1].cumsum()[::-1]
        res[0] = 0
        res = np.roll(res, -1)
        res /= self.mp_dx("eoy")
        return res

    def stat(self):
        return np.fmax(self.adj_rsv() + self.prem_rsv(), self.pricing.cv())

    pass

a = Stat(10513002)
print(a.stat())
