import time
from typing import Union
import pandas as pd

import sc_file_reader



class ResultData:
    def __init__(self, source: Union[sc_file_reader.FileReader, dict] = None, provider=None):
        self.fileName = None
        self.baseName = None
        self.dirName = None
        self.clearName = None
        self.suffix = None
        self.md5 = None
        self.provider = provider
        self.bizType = None
        self.dataTag = None
        self.parseTime = None

        self.extractTables = dict()

        if source is not None:
            if isinstance(source, sc_file_reader.FileReader):
                # for attr_name in self.__dict__:
                #     if hasattr(source, attr_name):
                #         setattr(self, attr_name, getattr(source, attr_name))
                self.fileName = source.filename
                self.baseName = source.basename
                self.dirName = source.dirname
                self.clearName = source.clear_name
                self.suffix = source.suffix
                self.md5 = source.md5
                self.provider = provider
            elif isinstance(source, dict):
                # for attr_name in self.__dict__:
                #     if attr_name in source:
                #         setattr(self, attr_name, source[attr_name])
                self.fileName = source['fileName']
                self.baseName = source['baseName']
                self.dirName = source['dirName']
                self.clearName = source['clearName']
                self.suffix = source['suffix']
                self.md5 = source['md5']
                self.provider = provider
            else:
                raise Exception('设置解析结果属性时，传入数据类型错误！')

    def to_dict(self):
        # self.parseTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.parseTime = float(time.strftime('%Y%m%d.%H%M%S', time.localtime()))
        return self.__dict__


class BusinessData:
    def __init__(self, source: Union[sc_file_reader.FileReader, dict] = None, provider=None):
        self.data = ResultData(source, provider)
        self.tables_structure = None
        self.personalization()

    def personalization(self):
        pass

    @property
    def result(self):
        for table_name in self.data.extractTables.keys():
            for row in self.data.extractTables[table_name]:
                for key in row.keys():
                    if isinstance(row[key], pd.Timestamp):
                        row[key] = row[key].strftime('%Y-%m-%d')

        return self.data.to_dict()

    def tables(self, table_name):
        if table_name not in self.tables_structure:
            raise Exception(f'业务数据中没有【{table_name}】表')

        if table_name not in self.data.extractTables:
            self.data.extractTables[table_name] = []

        return self.data.extractTables[table_name]

    def tables_append(self, table_name, row: dict, match_fields=True):
        self.tables(table_name).append(
            {field_name: row[field_name] if match_fields else row.get(field_name)
             for field_name in self.tables_structure[table_name]}
        )


class OptionBaseInfo(BusinessData):
    def personalization(self):
        # self.data.bizType = '场外期权'
        self.data.bizType = 'biz00009'
        self.data.dataTag = '基础信息'

        self.tables_structure = {
            '汇总信息': ['客户名称', '估值日期', '预付金_余额', '预付金_变动额', '名义本金_余额', '期权费_余额', '期权费_变动额', '累计盈亏'],
            '预付金变动流水': ['日期', '金额'],
            '名义本金流水': ['合约编号', '起始日', '到期日', '余额'],
            '期权费调整流水': ['合约编号', '日期', '余额', '发生额'],
            '合约累计盈亏': ['合约编号', '估值日期', '累计盈亏']
        }


class OptionSettlementInfo(BusinessData):
    def personalization(self):
        # self.data.bizType = '场外期权'
        self.data.bizType = 'biz00009'
        self.data.dataTag = '结算信息'

        self.tables_structure = {
            '汇总信息': ['客户名称', '估值日期', '当日_余额', '当日_发生额'],
            '结算明细': ['合约编号', '交易日', '交收日', '余额', '发生额'],
        }


class DealSlipBond(BusinessData):
    def personalization(self):
        # self.data.bizType = '银行间成交单'
        self.data.bizType = 'biz00008'
        self.data.dataTag = '债券'

        self.tables_structure = {
            '总体信息': ['标题', '成交日期', '成交编号', '页码'],

            '成交信息': ['买方', '卖方', '买方产品', '卖方产品', '债券代码', '债券名称', '净价(元/百)', '到期收益率(%)', '结算日',
                     '结算方式', '券面总额(万)', '结算金额(元)', '全价(元/百)', '应计利息(元/百)', '交易金额(元)', '应计利息总额(元)',
                     '行权收益率(%)'],

            '买方信息': ['机构', '投资管理人/产品', '法定代表人/地址', '交易员/电话', '资金账户户名', '资金开户行',
                     '资金账号/支付系统行号', '托管账户户名', '托管账号/托管机构'],

            '卖方信息': ['机构', '投资管理人/产品', '法定代表人/地址', '交易员/电话', '资金账户户名', '资金开户行',
                     '资金账号/支付系统行号', '托管账户户名', '托管账号/托管机构']
        }


class DealSlipRepurchase(BusinessData):
    def personalization(self):
        # self.data.bizType = '银行间成交单'
        self.data.bizType = 'biz00008'
        self.data.dataTag = '回购'

        self.tables_structure = {
            '总体信息': ['标题', '成交日期', '成交编号', '成交序列号'],

            '成交信息': ['正回购方', '逆回购方', '正回购方产品', '逆回购方产品', '回购期限(天)', '回购利率(%)', '交易金额(元)',
                     '到期结算金额(元)', '券面总额合计(万元)', '回购利息(元)', '首次结算方式', '到期结算方式', '首次结算日',
                     '到期结算日', '实际占款天数', '交易品种', '行权收益率(%)'],

            '成交信息-债券明细': ['债券代码', '债券名称', '券面总额(万元)', '折算比例(%)'],

            '正回购方信息': ['机构', '投资管理人/产品', '法定代表人', '地址', '交易员/电话', '资金账户户名', '资金开户行', '资金账号',
                       '支付系统行号', '托管账户户名', '托管账号', '托管机构'],

            '逆回购方信息': ['机构', '投资管理人/产品', '法定代表人', '地址', '交易员/电话', '资金账户户名', '资金开户行', '资金账号',
                       '支付系统行号', '托管账户户名', '托管账号', '托管机构']
        }


def data_print(d, le=0):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)) and len(v) > 0:
                print(f'{"-" * 4 * le}{k}:')
                data_print(v, le + 1)
            else:
                print(f'{"-" * 4 * le}{k}: {v}')
    elif isinstance(d, (list,)):
        for item in d:
            print(f'{"-" * 4 * le}{item}')
    else:
        print(f'{"-" * 4 * le}{d}:')
