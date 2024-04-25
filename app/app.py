import sys
import os
import configparser
import oracledb
import json
import logging
import mce

from ast import literal_eval
from sqlalchemy import URL, create_engine

from flask import Flask, request
from waitress import serve
from werkzeug.exceptions import HTTPException


def start_mce(config_filename):
    cfg = configparser.RawConfigParser()
    cfg.read(config_filename, encoding='utf-8')

    kw = {i[0]: i[1] if i[1].strip() != '' else None for i in cfg['engine_url'].items()}
    kw['query'] = {i[0]: i[1] for i in cfg['engine_url_query'].items() if i[1].strip() != ''}

    url = URL.create(**kw)

    if url.get_dialect().name == 'oracle':
        oracledb.version = "8.3.0"
        sys.modules["cx_Oracle"] = oracledb

        oracle_version = cfg['other'].get('oracle_version', '')
        if oracle_version == '11g':
            oracledb.init_oracle_client()

    kw = {i[0]: literal_eval(i[1]) for i in cfg['engine_other_params'].items()}

    eg = create_engine(url, **kw)

    check_interval = cfg['other'].get('check_interval', '')
    check_interval = int(check_interval) if check_interval.strip() != '' else 600

    mce.init(eg, check_interval)


app = Flask(__name__)


@app.route('/')
def welcome():
    return '欢迎使用计算引擎！版本号：%s' % mce.get_version()


@app.route('/help')
def helps():
    return '\n\n'.join(mce.helps()), 200, {'Content-Type': 'text/plain;charset=utf-8'}


@app.route('/run/<func_name>', methods=['POST'])
def run_mce_api(func_name):
    kwargs = request.get_json()

    if not isinstance(kwargs, dict):
        raise TypeError('参数格式错误，需要字典格式！')

    return mce.exec_api(func_name, **kwargs)


@app.errorhandler(HTTPException)
def framework_error(e):
    original = getattr(e, "original_exception", None)
    if original is not None:
        msg = repr(original)
    else:
        msg = e.description
    return json.dumps({'code': -2, 'msg': msg, 'data': None})


root_path = os.path.dirname(os.path.realpath(sys.argv[0]))
start_mce(os.path.join(root_path, 'boot.ini'))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        host, port = '0.0.0.0', 8085
    else:
        host, port = sys.argv[1].split(':')

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s,%(msecs)03d [%(thread)d] %(levelname)s %(name)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('MCE web application serving at %s:%s', host, port)

    serve(app, host=host, port=port)
