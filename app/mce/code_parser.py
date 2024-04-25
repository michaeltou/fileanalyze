import sys
import ast
import time

from functools import lru_cache, partial
from threading import RLock, current_thread, Thread
from contextlib import contextmanager
from io import StringIO

from .custom_cache import LRUTTLCache

_compile_filename = ''
_compile_cache_size = 1024 * 10
_std_types = (int, str, bool, float, set, tuple)


@lru_cache(maxsize=_compile_cache_size)
def _compile(source, co_id, mode='exec'):
    return compile(source, '%s[%s].%s' % (_compile_filename, co_id, mode), mode)
"mce.calc_objects[sc_file_reader].exec"

def _make_key(*args, **kwargs):
    key = [v if type(v) in _std_types else id(v) for v in args]
    key.extend([(k, v if type(v) in _std_types else id(v)) for k, v in kwargs.items()])
    return hash(tuple(key))


class AttrDict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")


@contextmanager
def _intercept_stdout():
    old = sys.stdout
    try:
        sys.stdout = StringIO()
        yield sys.stdout
    finally:
        sys.stdout = old


class CalcObject:
    def __init__(self, calc_object_manager, co_id, py_code='', py_expr='', lru_maxsize=0, ttl_seconds=0):
        self.__calc_object_manager = calc_object_manager

        self.__co_id = co_id
        self.__py_code = py_code
        self.__py_expr = py_expr
        self.__lru_maxsize = lru_maxsize
        self.__ttl_seconds = ttl_seconds

        self.__cache = None
        if lru_maxsize > 0 and ttl_seconds > 0:
            self.__cache = LRUTTLCache(lru_maxsize, ttl_seconds)

        self.__lock = RLock()
        self.__globals = None

    @property
    def co_id(self):
        return self.__co_id

    @property
    def py_code(self):
        return self.__py_code

    @property
    def py_expr(self):
        return self.__py_expr

    @property
    def lru_maxsize(self):
        return self.__lru_maxsize

    @property
    def ttl_seconds(self):
        return self.__ttl_seconds

    @property
    def cache(self):
        return self.__cache

    @property
    def globals(self):
        with self.__lock:
            if self.__globals is None:
                self.__globals = AttrDict()

                self.__globals['import_code'] = partial(
                    self.__calc_object_manager.import_code,
                    self.__globals
                )

                self.__globals['from_import_code'] = partial(
                    self.__calc_object_manager.from_import_code,
                    self.__globals
                )

                self.__globals.update(self.__calc_object_manager.kernel_funcs)

                exec(_compile(self.__py_code, self.co_id), self.__globals, self.__globals)
            return self.__globals

    def eval(self, **kwargs):
        return eval(_compile(self.py_expr, self.co_id, 'eval'), self.globals, kwargs)


class CalcObjectManager:
    def __init__(self, check_interval):
        self.__check_interval = check_interval

        self.__calc_objects = {}
        self.__lock = RLock()

        self.__kernel_funcs = {
            'calc_object_execute': self.eval,
            'coe': self.eval
        }

        check_thread = Thread(target=self.__check)
        check_thread.daemon = True
        check_thread.start()

    def __check(self):
        while True:
            time.sleep(self.__check_interval)
            with self.__lock:
                for co in self.__calc_objects.values():
                    if co.cache is not None:
                        co.cache.timeout_check()

    @property
    def kernel_funcs(self):
        return self.__kernel_funcs

    def set(self, co_id, **kwargs):
        with self.__lock:
            self.__calc_objects[co_id] = CalcObject(self, co_id, **kwargs)

    def get(self, co_id) -> CalcObject:
        with self.__lock:
            return self.__calc_objects[co_id]

    def delete(self, co_id):
        with self.__lock:
            del self.__calc_objects[co_id]

    def clear(self):
        with self.__lock:
            self.__calc_objects.clear()

    def is_exist(self, co_id):
        with self.__lock:
            return co_id in self.__calc_objects

    def import_code(self, target_namespace, co_id, alias: str = None):
        if alias is None:
            target_namespace[co_id] = self.get(co_id).globals
        else:
            target_namespace[alias] = self.get(co_id).globals

    def from_import_code(self, target_namespace, co_id, *args, **kwargs):
        gls = self.get(co_id).globals
        import_dict = {arg: gls[arg] for arg in args if arg not in kwargs}
        import_dict.update({v: gls[k] for k, v in kwargs.items()})
        target_namespace.update(import_dict if len(import_dict) > 0 else gls)

    def eval(self, co_id, **kwargs):
        if Evaluator.is_exist_current_evaluator():
            return Evaluator.get_current_evaluator().eval(co_id, **kwargs)
        else:
            evaluator = Evaluator.new_current_evaluator(self)
            try:
                return evaluator.eval(co_id, **kwargs)
            finally:
                Evaluator.del_current_evaluator()

    def trace(self, co_id, **kwargs):
        evaluator = Evaluator.new_current_evaluator(self, True)
        try:
            evaluator.eval(co_id, **kwargs)
            return evaluator.trace_info, evaluator.temp_cache
        finally:
            Evaluator.del_current_evaluator()

    def debug(self, py_code):
        with _intercept_stdout() as iso:
            try:
                _globals = self.__kernel_funcs.copy()
                _globals['import_code'] = partial(self.import_code, _globals)
                _globals['from_import_code'] = partial(self.from_import_code, _globals)
                exec(py_code, _globals, _globals)
                return iso.getvalue()
            except Exception as e:
                return repr(e)

    def get_params(self, co_id):
        calc_object = self.get(co_id)
        tree = ast.parse(calc_object.py_expr)
        defined_variables = set(calc_object.globals.keys())
        loaded_variables = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_variables.add(target.id)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                loaded_variables.add(node.id)
        return list(loaded_variables - defined_variables - {'locals'})

    def clear_cache(self):
        with self.__lock:
            for co in self.__calc_objects:
                if co.cache is not None:
                    co.cache.clear()


class Evaluator:
    _evaluators = {}

    @staticmethod
    def new_current_evaluator(calc_object_manager, is_trace=False):
        key = current_thread().ident
        Evaluator._evaluators[key] = Evaluator(calc_object_manager, is_trace)
        return Evaluator._evaluators[key]

    @staticmethod
    def del_current_evaluator():
        del Evaluator._evaluators[current_thread().ident]

    @staticmethod
    def get_current_evaluator():
        return Evaluator._evaluators[current_thread().ident]

    @staticmethod
    def is_exist_current_evaluator():
        return current_thread().ident in Evaluator._evaluators

    def __init__(self, calc_object_manager: CalcObjectManager, is_trace):
        self.__calc_object_manager = calc_object_manager
        self.__is_trace = is_trace

        self.__temp_cache = dict()
        self.__trace_info = []

        self.__serial_number = 0
        self.__stack = ['']

    @property
    def trace_info(self):
        return self.__trace_info

    @property
    def temp_cache(self):
        return self.__temp_cache

    def __eval(self, cache_key, co_id, **kwargs):
        if cache_key not in self.__temp_cache:
            calc_object = self.__calc_object_manager.get(co_id)
            if calc_object.cache is None:
                self.__temp_cache[cache_key] = calc_object.eval(**kwargs)
            else:
                self.__temp_cache[cache_key] = calc_object.cache.get(cache_key)
                if self.__temp_cache[cache_key] is None:
                    calc_object.cache.lock.acquire()
                    try:
                        self.__temp_cache[cache_key] = calc_object.eval(**kwargs)
                        calc_object.cache.put(cache_key, self.__temp_cache[cache_key])
                    finally:
                        calc_object.cache.lock.release()
        return self.__temp_cache[cache_key]

    def eval(self, co_id, **kwargs):
        cache_key = _make_key(co_id, **kwargs)

        if self.__is_trace:
            start_time = time.time()

            sn = 'sn-%d' % self.__serial_number
            self.__serial_number += 1

            parent_sn = self.__stack[-1]

            self.__stack.append(sn)
            try:
                return self.__eval(cache_key, co_id, **kwargs)
            finally:
                self.__trace_info.append({
                    'sn': sn,
                    'co_id': co_id,
                    'params': kwargs,
                    'result_key': cache_key,
                    'spend_time': time.time() - start_time,
                    'parent_sn': parent_sn
                })
                self.__stack.pop()
        else:
            return self.__eval(cache_key, co_id, **kwargs)
