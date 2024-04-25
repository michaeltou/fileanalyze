import pandas as pd

import sc_file_reader
import sc_mce_math
import uc_fam_fp_result



def parse(fn):
    # 第一步，读取文件
    fr = sc_file_reader.ExcelReader(fn)

    # 第二步，构造待用表格
    tables = {}

    # 资金汇总
    df = fr.sheet['资金汇总 Cash Summary']

    tables['资金汇总'] = df

    df = fr.sheet['场外期权 Option']
    df = fr.cut('场外期权 Option', pd.IndexSlice[2:, 'A':'O'])
    tables['场外期权'] = df
    column_names = df.columns.tolist()
    # print(column_names)

    # 第三步，给返回对象赋值
    ret_list = [uc_fam_fp_result.OptionBaseInfo(fr, '兴业证券'), uc_fam_fp_result.OptionSettlementInfo(fr, '兴业证券')]

    # 创建一个列表params，其中每个元素是一个字典，字典的键为返回对象的表格结构中的表格名，值为空字典。
    params = [
        {tb_name: dict() for tb_name in ret.tables_structure.keys()}
        for ret in ret_list
    ]

    # 将"期权估值报告"工作表中第1行、第B列的值赋给返回对象的第一个结果的"汇总信息"表格中的"客户名称"字段。
    params[0]['汇总信息']['客户名称'] = fr.sheet['资金汇总 Cash Summary'].loc[1, 'B']
    # 将"期权估值报告"工作表中第2行、第B列的值转换为datetime类型，并以'%Y年%m月%d日'的格式赋给返回对象的第一个结果的"汇总信息"表格中的"估值日期"字段。
    params[0]['汇总信息']['估值日期'] = pd.to_datetime(fr.sheet['资金汇总 Cash Summary'].loc[2, 'B'], format='%Y-%m-%d')
    params[0]['汇总信息']['预付金_余额'] = sc_mce_math.mce_round(fr.sheet['资金汇总 Cash Summary'].loc[6, 'B'], 2)
    params[0]['汇总信息']['预付金_变动额'] = None
    params[0]['汇总信息']['名义本金_余额'] = None
    params[0]['汇总信息']['累计盈亏'] = None
    params[0]['汇总信息']['期权费_余额'] = None
    params[0]['汇总信息']['期权费_变动额'] = None

    df = tables['场外期权']
    if not df.empty:
        def _do(x):
            ret_list[0].tables_append('名义本金流水', {
                '合约编号': x['合约编号\nTrade ID'],
                '起始日': pd.to_datetime(x['合约起始日\nTrade Date'], format='%Y-%m-%d'),
                '到期日': pd.to_datetime(x['合约到期日\nExpiry Date'], format='%Y-%m-%d'),
                '余额': sc_mce_math.mce_round(x['名义本金\nNotional Amount'], 2)
            })
            ret_list[0].tables_append('合约累计盈亏', {
                '合约编号': x['合约编号\nTrade ID'],
                '估值日期': params[0]['汇总信息']['估值日期'],
                '累计盈亏': sc_mce_math.mce_round(x['合约估值\nValuation'], 2)
            })
            ret_list[0].tables_append('期权费调整流水', {
                '合约编号': x['合约编号\nTrade ID'],
                '日期': params[0]['汇总信息']['估值日期'],
                '发生额': None,
                '余额': sc_mce_math.mce_round(x['期权费\nPremium'], 2)
            })

        df.apply(_do, axis=1)
    params[0]['汇总信息']['名义本金_余额'] = sc_mce_math.mce_round(df['名义本金\nNotional Amount'].sum(), 2)
    params[0]['汇总信息']['期权费_余额'] = sc_mce_math.mce_round(df['期权费\nPremium'].sum(), 2)
    params[0]['汇总信息']['累计盈亏'] = sc_mce_math.mce_round(df['合约估值\nValuation'].sum(),
                                                              2) - sc_mce_math.mce_round(df['期权费\nPremium'].sum(), 2)

    ret_list[0].tables_append('汇总信息', params[0]['汇总信息'])

    # print(params)
    params[1]['汇总信息']['当日_发生额'] = sc_mce_math.mce_round(fr.sheet['资金汇总 Cash Summary'].loc[6, 'D'], 2)
    ret_list[1].tables_append('汇总信息', {
        '客户名称': params[0]['汇总信息']['客户名称'],
        '估值日期': params[0]['汇总信息']['估值日期'],
        '当日_余额': None,
        '当日_发生额': params[1]['汇总信息']['当日_发生额']
    })

    return [ret.result for ret in ret_list]


file_name = 'XXX证券-私募证券投资基金-场外交易估值报告-2024-02-28.xlsx'
for r in parse(file_name):
    uc_fam_fp_result.data_print(r)







