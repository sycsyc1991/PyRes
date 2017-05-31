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
        建立某个责任，赋予uid，和两种赔付方式的uid
        
        Example:
        
        >>> ben1 = Benefit(1,1,1)
        
        :param int b_id: 责任uid 
        :param int uid_f: 责任赔付fix金额的uid
        :param int uid_p: 责任赔付prem金额的uid
        """
        self.b_id = b_id
        self.uid_f = uid_f
        self.uid_p = uid_p

    def get_parameter(self):
        """
        读取责任的参数
        
        :return:参数列表的Dataframe
        :rtype: tm.pd.Dataframe
        
        Example:
        >>> Benefit(1,1,1).get_parameter()
           benefit_id benefit_type       tbl_name
        0           1        death  CL_2000_1.csv
                
        """
        b_t = tm.ReadTable.get_ben_table()
        return b_t[b_t['benefit_id'] == self.b_id]

    def get_qx_tbl(self):
        """
        读取责任的发生率表
        
        :return: 发生率的Dataframe
        :rtype: tm.pd.Dataframe
        """
        tbl_name = self.get_parameter()['tbl_name'].values[0]
        return tm.ReadTable.get_mort_table(tbl_name)

    def get_ben_sa_fix(self, nb, np, age, polyr, mat):
        """
        根据参数确定保费相关保额

        :param nb: 保险期间
        :param np: 缴费期间
        :param int age: 被保险人年龄
        :param int polyr: 保单年度 
        :return: 保费相关保额
        :rtype: int
        """
        if self.uid_p == 0:
            ben = 0
        elif self.uid_p == 1 and (age < mat) and (age >= 0):
            ben = 1000
            # uid(1), sa = prem payed
        else:
            ben = 0
        return ben
    pass

    def get_ben_sa_p(self, nb, np, age, polyr, mat):
        """
        根据参数确定保费相关保额
        
        :param nb: 保险期间
        :param np: 缴费期间
        :param int age: 被保险人年龄
        :param int polyr: 保单年度 
        :return: 保费相关保额
        :rtype: int
        """
        if self.uid_p == 0:
            ben = 0
        elif self.uid_p == 1 and (age < mat) and (age >= 0):
            ben = min(np, polyr)
            # uid(1), sa = prem payed
        elif self.uid_p == 2 and (age < mat) and (age >= 0):
            ben = 1.05 * min(np, polyr)
            # uid_p(2), sa = 1.05 * prem payed
        else:
            ben = 0
        return ben


class Db(Benefit):
    """
    死亡责任类，规定BEN_TYPE为death

    Example:
    >>> db1 = Db(1,1,1)
    
    """
    BEN_TYPE = "death"

    def __init__(self, b_id, uid_f, uid_p):
        Benefit.__init__(self, b_id, uid_f, uid_p)

    pass


class Acc(Benefit):
    """
    死亡责任类，规定BEN_TYPE为death

    Example:
    >>> ac1 = Acc(1,1,1)

    """
    BEN_TYPE = "acc"


class Ci(Benefit):
    """
    死亡责任类，规定BEN_TYPE为death

    Example:
    >>> ci1 = Ci(1,1,1)

    """
    BEN_TYPE = "ci"

    def __init__(self, b_id, uid_f, uid_p):
        Benefit.__init__(self, b_id, uid_f, uid_p)

    pass

class Ann(Benefit):
    """
    年金类，规定BEN_TYPE为ann
    """
    BEN_TYPE = "ann"

    def __init__(self, b_id, uid_f, uid_p):
        Benefit.__init__(self, b_id, uid_f, uid_p)

    def get_ben_sa_fix(self, nb, np, age, polyr, mat):
        """
        根据参数确定固定保额

        :param nb: 保险期间
        :param np: 缴费期间
        :param int age: 被保险人年龄
        :param int polyr: 保单年度 
        :return: 固定保额
        :rtype: int
        """
        if self.uid_f == 2:
            # uid(2) , sa = ann 1000 sa
            if polyr == 3:
                ben = 300
            elif age == 59:
                ben = 600
            elif (age < (mat-1)) and (age > 59):
                ben = 200
            elif (polyr <= 2) or (age >= (mat-1)):
                ben = 0
            else:
                ben = 100
        return ben


class Plan(object):
    """
    险种基础类，读取险种，险种类型，险种包含的责任
    """
    def __init__(self, plan_id):
        """
        
        Example:
        
        >>> plan = Plan(10513002)
        
        :param int plan_id: 险种代码 
        """
        self.plan_id = plan_id
    # Plan类以plan_id为索引

    def plan_type(self):
        """

        Example:
        

        :return: 险种类型参数
        :rtype: tm.pd.Dataframe
        """
        pb_t = tm.ReadTable.get_plan_table()
        pb_t = pb_t[pb_t['plan_id'] == self.plan_id]
        return pb_t

    def plan_benefit(self):
        pb_t = tm.ReadTable.get_plan_table()
        pb_t = pb_t[pb_t['plan_id'] == self.plan_id]
        return pb_t[['benefit_type', 'benefit_id', 'sa_uid_f', 'sa_uid_p']]
    # 读取Plan下的责任列表

    def plan_benifit_count(self):
        b_count = len(self.plan_benefit().index)
        return b_count
    # 责任个数


class PricingOd(object):
    """
    产品定价模块
    """
    def __init__(self, plan_id):
        """
        给定险种代码
        :param int plan_id: 险种代码 
        """
        self.plan_id = plan_id
    # IssAge = 30
    # sa = 1000
    # sex = 0
    # payterm = 10
    # insterm = 76
    # load_tbl_name = "Loading_10513002"
    # IntRate = 0.035
    # IntRate_CV = 0.055

    IssAge = 30
    sa = 1000
    sex = 0
    payterm = 10
    insterm = 50
    load_tbl_name = "Loading_20313001"
    IntRate = 0.025
    IntRate_CV = 0.045
    mat = 80

    def plan(self):
        return Plan(self.plan_id)
    # 读取Plan类的属性

    @staticmethod
    def get_ben(b_id, b_type, uid_f, uid_p):
        """
        
        :param int b_id: 
        :param str b_type: 
        :param int uid_f: 
        :param int uid_p: 
        :return: Benefit类
        :rtype: Benefit
        """
        if b_type == "death":
            ben = Db(b_id, uid_f, uid_p)
        elif b_type == "ci":
            ben = Ci(b_id, uid_f, uid_p)
        elif b_type == "annuity":
            ben = Ann(b_id, uid_f, uid_p)
        else:
            ben = Benefit(b_id,uid_f,uid_p)
        return ben
    # 根据type生成Ben类

    def ben_list(self):
        """
        获取险种对应的Benefit类的list
        :return: Benefit类的list
        :rtype: list
        """
        ids = list(self.plan().plan_benefit()['benefit_id'].values)
        types = list(self.plan().plan_benefit()['benefit_type'].values)
        uid_f = list(self.plan().plan_benefit()['sa_uid_f'].values)
        uid_p = list(self.plan().plan_benefit()['sa_uid_p'].values)
        ben_l = list(map(self.get_ben, ids, types, uid_f, uid_p))
        return ben_l
    # 读表获取plan下的Ben类

    # def ben_dict(self):
    #     ids = list(self.plan().plan_benifit()['benifits_id'].values)
    #     types = list(self.plan().plan_benifit()['benifits_type'].values)
    #     bens = map(self.get_ben, ids, types)
    #     return dict(zip(types, bens))
    # # 读表获取plan下的Ben类

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

    @staticmethod
    def get_ben_sa_fix(ben):
        """
        
        :param ben: 
        :return: 生成benefit的fix_sa的获取函数
        """
        get_ben_sa_np = np.frompyfunc(ben.get_ben_sa_fix, 5, 1)
        return get_ben_sa_np

    def mp_ben_fix(self, ben):
        return self.get_ben_sa_fix(ben)(self.insterm, self.payterm, self.apv_mp_age(), self.apv_mp_polyr())

    @staticmethod
    def get_ben_sa_prem(ben):
        """

        :param ben: 
        :return: 生成benefit的prem_sa的获取函数
        """
        get_ben_sa_np = np.frompyfunc(ben.get_ben_sa_p, 5, 1)
        return get_ben_sa_np

    def mp_ben_prem(self, ben):
        return self.get_ben_sa_prem(ben)(self.insterm, self.payterm, self.apv_mp_age(), self.apv_mp_polyr(), self.mat)
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
        if (ben.BEN_TYPE == "ann") or (ben.BEN_TYPE == "endow"):
            qx = np.zeros(len(self.apv_mp_age()))
        else:
            qx = self.get_qx_list(sex, ben.get_qx_tbl())
        if [x for x in self.ben_list() if x.BEN_TYPE == "ci"].__len__() != 0:
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

    @staticmethod
    def get_load_list(payterm, tbl_name):
        tbl_name = tbl_name + ".csv"
        # tbl_name_firstyear = tbl_name + "_Firstyear.csv"
        tbl = tm.ReadTable.get_load_table(tbl_name)
        load_list = tbl[str(payterm)]
        return load_list
    # TODO 拆分首年loading

    def mp_ld(self):
        """
        
        :return: loading列 
        :rtype: np.ndarray
        """
        loading = self.get_load_list(self.payterm, self.load_tbl_name).values
        loading[np.isnan(loading)] = 0
        return loading[:len(self.apv_mp_age())]

    def mp_netp(self):
        """
        
        :return: NP因子
        :rtype: np.ndarray
        """
        prem = np.zeros(len(self.apv_mp_age()), dtype='int32')
        prem[:self.payterm] = 1
        netp = (prem - self.mp_ld()) * self.mp_dx("boy")
        return netp
    # TODO: 待区分付款与保障lx与db

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
        """
        
        :param phase: 时间节点 
        :return: Dx换算函数
        """
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_bop() / (1 + self.IntRate) ** (self.apv_mp_polyr() - adj[phase])
        return dx

    # Dx calculate

    def mp_cx(self, ben):
        """
        
        :param ben: 责任 
        :return: Cx换算函数
        """
        if ben.BEN_TYPE is "ann":
            cx = self.mp_lx_eop() / (1 + self.IntRate) ** (self.apv_mp_polyr())
        else:
            cx = self.mp_dx("moy") * self.mp_qx_ben_list(ben)
        return cx
    # Cx calculate

    def mp_ben_fix_sum(self, ben):
        return sum(self.mp_cx(ben) * self.mp_ben_fix(ben))

    def mp_plan_fix(self):
        return map(self.mp_ben_fix_sum, self.ben_list())

    def mp_ben_prem_sum(self, ben):
        return sum(self.mp_cx(ben) * self.mp_ben_prem(ben))

    def mp_plan_prem(self):
        return map(self.mp_ben_prem_sum, self.ben_list())

    def mp_end(self):
        if self.plan.plan_type() is "Endowment":
            endow =
        else:
            endow = 0
        return endow

    def gp(self):
        """
        普通险保费计算公式
        :return: 标准SA对应的保费,取2位小数
        :rtype: np.float64
        """
        return round(sum(self.mp_plan_fix())/(sum(self.mp_netp()) - sum(self.mp_plan_prem())), 2)

    def mp_dx_cv(self, phase="moy"):
        """
        CV的换算函数
        :param phase: 
        :return: 
        """
        adj = {
            "boy": 1,
            "moy": 0.5,
            "eoy": 0
        }
        dx = self.mp_lx_bop() / (1 + self.IntRate_CV) ** (self.apv_mp_polyr() - adj[phase])
        return dx


    def mp_cx_cv(self, ben):
        cx = self.mp_dx_cv() * self.mp_qx_ben_list(ben)
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

    def cv(self):
        k = 0.8
        r = np.fmin(k + self.apv_mp_polyr() * (1 - k) / np.fmin(20, self.payterm), 1)
        cv = self.pvr() * r
        return cv

    pass


if __name__ == '__main__':
    a = PricingOd(20313001)
    a1 = a.ben_list()[1]
    b = a.mp_cx(a1) * a.mp_ben_fix(a1)
    print(a.mp_dx("boy"))
    # print(a.mp_qx_ben_list(a.ben_list()))
    print(b)

