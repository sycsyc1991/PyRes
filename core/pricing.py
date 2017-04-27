# -*- coding:utf-8 -*-

"""
This module defined the pricing module for ordinary life insurance products

including
..py:class:: Benefit 责任
..py:class:: Plan 险种信息
..py:class:: PricingOd 定价模块


"""


import numpy as np
import core.tbl_manage as tm
from functools import reduce
#from peewee import *
#from playhouse import postgres_ext as pge
import os


class Benefit(object):
    """
    责任基础类，获取发生率表，赔付表

    """

    def __init__(self, b_id, uid_f, uid_p):
        """
        
        Example:
        
        >>> ben1 = Benefit(1,1,1)
        
        >>> Benefit(1,1,1).get_parameter()
           benifit_id benifits_type       tbl_name
        0           1         death  CL_2000_1.csv
        
        :param int b_id: 责任uid 
        :param int uid_f: 责任赔付fix金额的uid
        :param int uid_p: 责任赔付prem金额的uid
        """
        self.b_id = b_id
        self.uid_f = uid_f
        self.uid_p = uid_p

    def get_parameter(self):
        """
        
        :return:
        :rtype: tm.pd.DataFrame
        """
        b_t = tm.ReadTable.get_ben_table()
        return b_t[b_t['benifit_id'] == self.b_id]

    def get_qx_tbl(self):
        tbl_name = self.get_parameter()['tbl_name'].values[0]
        return tm.ReadTable.get_mort_table(tbl_name)

    def get_ben_sa_fix(self, nb, np, age, polyr):
        if self.uid_f == 0:
            ben = 0
        elif self.uid_f == 1 and (age <= 105) and (age >= 0) and polyr <= 105:
            ben = 1000
            # uid(1) , sa = fixed 1000
        return ben

    def get_ben_sa_p(self, nb, np, age, polyr):
        if self.uid_p == 0:
            ben = 0
        elif self.uid_p == 1 and (age <= 105) and (age >= 0):
            ben = min(np, polyr)
            # uid(1), sa = prem payed
        return ben


class Db(Benefit):
    BEN_TYPE = "death"

    def __init__(self, b_id, uid_f, uid_p):
        Benefit.__init__(self, b_id, uid_f, uid_p)

    pass


class Acc(object):

    BEN_TYPE = "acc"


class Ci(Benefit):
    BEN_TYPE = "ci"

    def __init__(self, b_id, uid_f, uid_p):
        Benefit.__init__(self, b_id, uid_f, uid_p)

    pass


class Plan(object):

    def __init__(self, plan_id):
        self.plan_id = plan_id
    # Plan类以plan_id为索引

    def plan_type(self):
        pb_t = tm.ReadTable.get_plan_table()
        pb_t = pb_t[pb_t['plan_id'] == self.plan_id]
        return pb_t

    def plan_benifit(self):
        pb_t = tm.ReadTable.get_plan_table()
        pb_t = pb_t[pb_t['plan_id'] == self.plan_id]
        return pb_t[['benifits_type', 'benifits_id', 'sa_uid_f', 'sa_uid_p']]
    # 读取Plan下的责任列表

    def plan_benifit_count(self):
        b_count = len(self.plan_benifit().index)
        return b_count
    # 责任个数

class PricingOd(object):

    def __init__(self, plan_id):
        self.plan_id = plan_id
    IssAge = 30
    sa = 1000
    sex = 0
    payterm = 10
    insterm = 75
    load_tbl_name = "Loading_10513002"
    IntRate = 0.035
    IntRate_CV = 0.055

    def plan(self):
        return Plan(self.plan_id)
    # 读取Plan类的属性

    @staticmethod
    def get_ben(b_id, b_type, uid_f, uid_p):
        if b_type == "death":
            ben = Db(b_id, uid_f, uid_p)
        elif b_type == "ci":
            ben = Ci(b_id, uid_f, uid_p)
        return ben
    # 根据type生成Ben类

    def ben_list(self):
        ids = list(self.plan().plan_benifit()['benifits_id'].values)
        types = list(self.plan().plan_benifit()['benifits_type'].values)
        uids_f = list(self.plan().plan_benifit()['sa_uid_f'].values)
        uids_p = list(self.plan().plan_benifit()['sa_uid_p'].values)
        bens = list(map(self.get_ben, ids, types, uids_f, uids_p))
        return bens
    # 读表获取plan下的Ben类

    def ben_dict(self):
        ids = list(self.plan().plan_benifit()['benifits_id'].values)
        types = list(self.plan().plan_benifit()['benifits_type'].values)
        bens = map(self.get_ben, ids, types)
        return dict(zip(types, bens))
    # 读表获取plan下的Ben类

    def apv_mp_age(self):
        if self.insterm == "105@":
            mp_age = np.array(range(self.IssAge, 106, 1), dtype='int32')
        else:
            mp_age = np.array(range(self.IssAge, self.IssAge + self.insterm, 1), dtype='int32')
        return mp_age
    # 生成model points对应的age列

    def apv_mp_polyr(self):
        polyr = np.arange(len(self.apv_mp_age()), dtype='int32') + 1
        return polyr
    # 生成model points对应的保单难度列

    def get_ben_sa_fix(self, ben):
        get_ben_sa_np = np.frompyfunc(ben.get_ben_sa_fix, 4, 1)
        return get_ben_sa_np

    def mp_ben_fix(self, ben):
        return self.get_ben_sa_fix(ben)(self.insterm, self.payterm,
                                        self.apv_mp_age(), self.apv_mp_polyr())

    def get_ben_sa_prem(self, ben):
        get_ben_sa_np = np.frompyfunc(ben.get_ben_sa_p, 4, 1)
        return get_ben_sa_np

    def mp_ben_prem(self, ben):
        return self.get_ben_sa_prem(ben)(self.insterm, self.payterm,
                                        self.apv_mp_age(), self.apv_mp_polyr())
    # 生成model points中某个ben对应的sa列

    # def mp_ben_fix(self):
    #     ben_fix = np.zeros(len(self.apv_mp_age()), dtype='int32')
    #     for age in (self.apv_mp_age()):
    #         ben_fix[self.IssAge - age] = self.get_ben(1, "death").get_ben_sa(age, 1)
    #     return ben_fix
    #
    # @staticmethod
    # def get_qx_list(age, sex, tbl):
    #     if sex == 0:
    #         sel = "male"
    #     else:
    #         sel = "female"
    #     qx_list = tbl[tbl.age >= age][sel]
    #     return qx_list

    def get_qx_list(self, sex, tbl):
        qx_list = tbl[tbl['age'].isin(self.apv_mp_age())]["male" if sex == 0 else "female"]
        return qx_list
    # 读取tbl中的model points对应的行

    def mp_qx_ben(self, ben):
        tbl = [x.get_qx_tbl for x in ben]
        qx = self.get_qx_list(self.sex, tbl).values
        if ben.BEN_TYPE == "death":
            qx = qx * (1 - self.get_qx_list(self.sex, tm.ReadTable.get_mort_table("K_2000_1.csv")).values)
        return qx
    # 读取ben对应的model points的qx

    @staticmethod
    def get_load_list(payterm, tbl_name):
        tbl_name = tbl_name + ".csv"
        # tbl_name_firstyear = tbl_name + "_Firstyear.csv"
        tbl = tm.ReadTable.get_load_table(tbl_name)
        load_list = tbl[str(payterm)]
        return load_list
    # TODO 拆分首年loading

    # def mp_qx(self, ben):
    #     qx = self.get_qx_list(self.IssAge, self.sex, ben.get_qx_tbl()).values
    #     return qx[:len(self.apv_mp_age())]

    def mp_ld(self):
        loading = self.get_load_list(self.payterm, self.load_tbl_name).values
        loading[np.isnan(loading)] = 0
        return loading[:len(self.apv_mp_age())]

    def mp_netp(self):
        prem = np.zeros(len(self.apv_mp_age()), dtype='int32')
        prem[:self.payterm] = 1
        netp = (prem - self.mp_ld()) * self.mp_dx()
        return netp
    # TODO: 待区分付款与保障lx与db

    @staticmethod
    def lx_cal(lx, qx):
        return lx - qx
    # 单一死亡人数减去

    def mp_lx_init(self):
        lx = np.ones(len(self.apv_mp_age()))
        return lx

    def mp_lx_cal(self):
        if [x for x in self.ben_list() if x.BEN_TYPE == "death"].__len__() != 1:
            raise NotImplementedError("death benifit number error")
        # db部分处理
        ben_death = [x for x in self.ben_list() if x.BEN_TYPE == "death"]
        # ben_death = filter(lambda x: x.BEN_TYPE == "death", self.ben_list())[0]
        ben_ci = [x for x in self.ben_list() if x.BEN_TYPE == "ci"]
        # ben_ci = filter(lambda x: x.BEN_TYPE == "ci", self.ben_list())[0]
        lx = self.mp_lx_init()
        qx = self.mp_qx_ben(ben_death)
        cix = self.mp_qx_ben(ben_ci)
        for i in self.apv_mp_polyr()[:-1]-1:
            lx[i+1] = reduce(self.lx_cal, (lx[i], lx[i] * qx[i], lx[i] * cix[i]))
        return lx

    # def mp_lx(self, lx_init):
    #     lx = lx_init
    #     for age in (self.apv_mp_age()):
    #         if age - self.IssAge == 0:
    #             lx[age - self.IssAge] = 1
    #         else:
    #             lx[age - self.IssAge] = lx[age - self.IssAge - 1] * \
    #                 (1 - self.mp_qx(Db(1))[age - self.IssAge - 1])
    #     return lx
        # TODO: 待区分付款与保障lx与db

    def mp_dx(self, phase="moy"):
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_cal() / (1 + self.IntRate) ** (self.apv_mp_polyr() - adj[phase])
        return dx

    # Dx calculate

    def mp_cx(self, ben):
        cx = self.mp_dx() * self.mp_qx_ben(ben) / ((1 + self.IntRate) ** 0.5)
        return cx
    # Cx calculate

    def mp_ben_fix_sum(self, ben):
        return sum(self.mp_cx(ben) * self.mp_ben_fix(ben))

    def apv_ben_fix(self):
        return map(self.mp_ben_fix_sum, self.ben_list())

    def mp_ben_prem_sum(self, ben):
        return sum(self.mp_cx(ben) * self.mp_ben_prem(ben))

    def apv_ben_prem(self):
        return map(self.mp_ben_prem_sum, self.ben_list())

    def gp(self):
        return round(sum(self.apv_ben_fix())/(sum(self.mp_netp()) - sum(self.apv_ben_prem())), 2)

    # CV part
    def mp_dx_cv(self, phase="moy"):
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_cal() / (1 + self.IntRate_CV) ** (self.apv_mp_polyr() - adj[phase])
        return dx

    # Dx calculate

    # Dx calculate

    def mp_cx_cv(self, ben):
        cx = self.mp_dx_cv() * self.mp_qx_ben(ben)
        return cx

    def mp_netp_cv(self):
        prem = np.zeros(len(self.apv_mp_age()), dtype='int32')
        prem[:self.payterm] = 1
        netp = (prem - self.mp_ld()) * self.mp_dx_cv("boy")
        return netp

    def mp_ben_fix_cv(self, ben):
        return self.mp_cx_cv(ben) * self.mp_ben_fix(ben)

    def apv_ben_fix_cv(self):
        return map(self.mp_ben_fix_cv, self.ben_list())

    def apv_ben_fix_list(self):
        ben_out_list = map(self.mp_ben_fix_cv, self.ben_list())
        return ben_out_list

    # 单个ben（prem类型）的apv计算

    def mp_ben_prem_cv(self, ben):
        return self.mp_cx_cv(ben) * self.mp_ben_prem(ben)

    def apv_ben_prem_list(self):
        return map(self.mp_ben_prem_cv, self.ben_list())

    # ben list（prem类型）的apv

    def apv_ben_total_cv(self):
        return reduce(lambda x, y: x+y, self.apv_ben_fix_list()) + (self.gp() * reduce(lambda x, y: x+y, self.apv_ben_prem_list()))

    def gp_cv(self):
        return sum(self.apv_ben_total_cv()) / sum(self.mp_netp_cv())

    def pvr(self):
        pvr = self.apv_ben_total_cv() - np.float64(self.gp_cv()) * self.mp_netp_cv()
        pvr = np.roll(pvr[::-1].cumsum()[::-1] / self.mp_dx_cv("boy"), -1)
        return pvr

    pass

# a = PricingOd(10513002)
# print(a.pvr())

