import inspect
import json

from concurrent.futures import ProcessPoolExecutor

from .db_models import create_tables, MceCalcObjectInfo
from .db_operator import DBOperator
from .code_parser import CalcObjectManager

_version = '3.0.0'

_db_operator: DBOperator
_calc_object_manager: CalcObjectManager
_api = {}


def get_version():
    """
    获得计算引擎版本号
    :return: 版本号
    """
    return _version


def init(engine, cache_check_interval=60 * 10):
    """
    初始化计算引擎
    :param engine: sqlalchemy数据库引擎
    :param cache_check_interval: 缓存检查时间间隔
    :return: None

    传入的engine确定了连接的数据库，若该库中没有计算对象信息表，会自动创建；若存在计算对象信息表，会把所有的计算对象加载到对象管理员实例中
    并且将外部调用函数发布到api函数列表中，供外部调用
    """
    create_tables(engine)

    global _db_operator, _calc_object_manager
    _db_operator = DBOperator(engine, MceCalcObjectInfo)
    _calc_object_manager = CalcObjectManager(cache_check_interval)

    reload()

    publish()


def _to_co_attr(params: dict):
    mapping = {
        'co_id': 'object_id',
        'py_code': 'python_code',
        'py_expr': 'python_expr',
        'lru_maxsize': 'lru_maxsize',
        'ttl_seconds': 'ttl_seconds'
    }
    ret = {}
    for k, v in mapping.items():
        if v in params:
            ret[k] = params[v]
    return ret


def add(**kwargs):
    """
    添加计算对象
    :param kwargs: 动态参数字典
    :return: None

    字段信息：
        object_id = Column(String(50), primary_key=True)
        object_name = Column(String(50))
        custom_tag = Column(CHAR(1))
        parent_id = Column(String(50))
        python_code = Column(Text)
        python_expr = Column(String(200))
        lru_maxsize = Column(Integer, default=0)
        ttl_seconds = Column(Integer, default=0)
        remark = Column(String(200))
        sort_number = Column(Integer, default=0)

        object_id: 对象编号，主键，不能重复，是唯一标识，后续都需要用到此字段查找计算对象
        object_name: 对象名称，使用中文表示
        custom_tag: 自定义标签，用来对计算对象进行分类管理
        parent_id: 父节点编号，做树形展示使用
        python_code: 顾名思义，用python写的代码块，相当于python模块的概念
        python_expr: python表达式，主要用于对象计算结果的返回，也可以称为返回结果表达式
        lru_maxsize: lru淘汰算法，最大缓存数量
        ttl_seconds: ttl淘汰算法，最大缓存时间，单位是-秒
        remark: 备注
        sort_number: 排序编号，用于显示的先后次序
    """
    _db_operator.add(**kwargs)
    _calc_object_manager.set(**_to_co_attr(kwargs))


def delete(object_id):
    """
    删除计算对象
    :param object_id: 对象编号
    :return: 影响记录数

    先从数据库把计算对象信息删除，然后再从计算对象管理器中删除
    """
    ret = _db_operator.delete(MceCalcObjectInfo.object_id == object_id)
    _calc_object_manager.delete(object_id)
    return ret


def update(object_id, **kwargs):
    """
    修改计算对象
    :param object_id: 对象编号（主键）
    :param kwargs: 动态参数字典，需要修改的字典
    :return: 影响记录数

    字段信息：
        object_id = Column(String(50), primary_key=True)
        object_name = Column(String(50))
        custom_tag = Column(CHAR(1))
        parent_id = Column(String(50))
        python_code = Column(Text)
        python_expr = Column(String(200))
        lru_maxsize = Column(Integer, default=0)
        ttl_seconds = Column(Integer, default=0)
        remark = Column(String(200))
        sort_number = Column(Integer, default=0)

        object_id: 对象编号，主键，不能重复，是唯一标识，后续都需要用到此字段查找计算对象
        object_name: 对象名称，使用中文表示
        custom_tag: 自定义标签，用来对计算对象进行分类管理
        parent_id: 父节点编号，做树形展示使用
        python_code: 顾名思义，用python写的代码块，相当于python模块的概念
        python_expr: python表达式，主要用于对象计算结果的返回，也可以称为返回结果表达式
        lru_maxsize: lru淘汰算法，最大缓存数量
        ttl_seconds: ttl淘汰算法，最大缓存时间，单位是-秒
        remark: 备注
        sort_number: 排序编号，用于显示的先后次序
    """
    ret = _db_operator.update(MceCalcObjectInfo.object_id == object_id, **kwargs)
    if ret > 0:
        coi = _db_operator.query(MceCalcObjectInfo.object_id == object_id)[0]
        _calc_object_manager.set(**_to_co_attr(coi.to_dict()))
    return ret


def query(**kwargs):
    """
    查询计算对象
    :param kwargs: 动态参数字典
    :return: 计算对象信息列表

    kwargs可传入相关条件，多个条件间的关系是：and，不传则返回全部记录
    """
    return _db_operator.query(*[getattr(MceCalcObjectInfo, k) == v for k, v in kwargs.items()])


def get_params(object_id):
    """
    获得计算对象参数
    :param object_id: 计算对象编号
    :return: 参数列表

    获得返回表达式所需的参数
    """
    return _calc_object_manager.get_params(object_id)


def execute(object_id, **kwargs):
    """
    执行计算对象
    :param object_id: 计算对象编号
    :param kwargs: 动态参数字典（不知道传什么可以调用get_params查看）
    :return: python_expr表达式的返回结果
    """
    return _calc_object_manager.eval(object_id, **kwargs)


def trace(object_id, **kwargs):
    """
    追踪计算对象
    :param object_id: 计算对象编号
    :param kwargs: 动态参数字典（不知道传什么可以调用get_params查看）
    :return: 执行计划树形结构
    """
    return _calc_object_manager.trace(object_id, **kwargs)


def _debug(py_code):
    """
    调试代码
    :param py_code: python代码
    :return: 调试结果
    """
    return _calc_object_manager.debug(py_code)


def debug(py_code):
    """
    调试代码-独立进程
    :param py_code: python代码
    :return: 调试结果
    """
    with ProcessPoolExecutor(max_workers=1) as exe:
        return exe.submit(_debug, py_code).result()


def reload():
    """
    重新加载计算对象
    主要是防止有人从后台数据库直接插入计算对象信息，这样计算引擎需要重新加载
    :return:
    """
    _calc_object_manager.clear()
    for coi in _db_operator.query():
        _calc_object_manager.set(**_to_co_attr(coi.to_dict()))


def clear_cache():
    """
    清空计算缓存
    当使用的数据发生变化时（数据库中的数据发生变化时），需要掉用此函数清除计算中的缓存数据，这样才会从数据库中重新取数据
    :return: None
    """
    _calc_object_manager.clear_cache()


def publish():
    """
    发布api
    :return: None
    """
    _api['get_version'] = get_version

    _api['add'] = add
    _api['delete'] = delete
    _api['update'] = update
    _api['query'] = query

    _api['get_params'] = get_params
    _api['execute'] = execute
    _api['trace'] = trace
    _api['debug'] = debug

    _api['reload'] = reload
    _api['clear_cache'] = clear_cache


def exec_api(api_func_name, json_encoder_name='api_json_encoder', *args, **kwargs):
    """
    执行计算引擎api函数
    :param api_func_name: 函数名
    :param json_encoder_name: json编码器
    :param args: 动态参数列表
    :param kwargs: 动态参数字典
    :return: json对象
    """
    json_encoder = None
    if _calc_object_manager.is_exist(json_encoder_name):
        json_encoder = execute(json_encoder_name)

    func = _api[api_func_name]
    try:
        data = func(*args, **kwargs)
        return json.dumps({'code': 0, 'msg': None, 'data': data}, cls=json_encoder)
    except Exception as e:
        return json.dumps({'code': -1, 'msg': repr(e), 'data': None})


def helps():
    """
    获得所有api的帮助信息
    :return: 帮助信息列表
    """
    return ['%s%s%s' % (k, inspect.signature(v), v.__doc__) for k, v in _api.items()]
