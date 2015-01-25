
from copy import deepcopy
import logging
import sys

import pytest
import mock
import flask
import logconfig

from flask_logconfig import (
    LogConfig,
    FlaskQueueHandler,
    FlaskLogConfigException,
    request_context_from_record
)


parametrize = pytest.mark.parametrize

logging_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG'
    }
}


class RequestHandlerConfig(object):
    LOGCONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'request': {
                'class': 'tests.test_flask_logconfig.RequestHandlerFromRecord'
            }
        },
        'root': {
            'handlers': ['request'],
            'level': 'DEBUG'
        }
    }
    LOGCONFIG_QUEUE = ['']


class RequestHandlerFromRecord(logging.Handler):
    def emit(self, record):
        with request_context_from_record(record):
            sys.stdout.write(flask.request.url)


@pytest.fixture(scope='function')
def app(request):
    """Provide instance for basic Flask app."""
    app = flask.Flask(__name__)
    return app


@pytest.fixture(scope='function')
def testapp(request, app):
    """Return basic Flask app with an established app context."""
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)

    return app


def init_app(app, settings):
    app.config.from_object(settings)
    logcfg = LogConfig()
    logcfg.init_app(app)
    return logcfg


@parametrize('config,funcall', [
    (logging_dict, 'logconfig.loaders.from_dict'),
    ('logging.json', 'logconfig.loaders.from_json'),
    ('logging.yml',  'logconfig.loaders.from_yaml'),
    ('logging.yaml',  'logconfig.loaders.from_yaml'),
    ('logging.cfg',  'logconfig.loaders.from_file'),
    ('logging.ini',  'logconfig.loaders.from_file'),
    ('logging.conf',  'logconfig.loaders.from_file'),
    ('logging.config',  'logconfig.loaders.from_file'),
])
def test_config_value_logging(app, config, funcall):
    class Config:
        LOGCONFIG = config

    with mock.patch(funcall) as patched:
        init_app(app, Config)
        patched.assert_called_once_with(Config.LOGCONFIG)


def test_config_value_logconfig_queue(app):
    class Config:
        LOGCONFIG_QUEUE = ['logconfig', 'customlogger']

    with mock.patch('logconfig.queuify_logger') as patched:
        logcfg = init_app(app, Config)

        assert patched.called
        assert patched.call_count == len(Config.LOGCONFIG_QUEUE)

        for idx, name in enumerate(Config.LOGCONFIG_QUEUE):
            assert patched.mock_calls[idx][1][0] == name

        with app.app_context():
            assert len(logcfg.get_listeners()) == len(Config.LOGCONFIG_QUEUE)


@parametrize('names,handlers', [
    (['custom1'], ['null1']),
    (['custom1'], ['null1', 'null2']),
    (['custom1', 'custom2'], ['null1']),
    (['custom1', 'custom2'], ['null1', 'null2']),
])
def test_logconfig_queue_creation(app, names, handlers):
    class Config:
        LOGCONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'handlers': {},
            'loggers': {}
        }

        LOGCONFIG_QUEUE = names

    for handler in handlers:
        Config.LOGCONFIG['handlers'][handler] = {
            'class': 'logging.StreamHandler'
        }

    for name in names:
        Config.LOGCONFIG['loggers'][name] = {'handlers': handlers}

    logcfg = init_app(app, Config)
    logger = logging.getLogger(name)

    assert len(logcfg.listeners) == len(names)

    for name in names:
        logger = logging.getLogger(name)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], FlaskQueueHandler)
        assert len(logcfg.listeners[name].handlers) == len(handlers)

    logcfg.stop_listeners()


@parametrize('handler_class', [
    'tests.test_flask_logconfig.RequestHandlerFromRecord',
])
def test_logconfig_queue_request_context(app, capsys, handler_class):
    config = RequestHandlerConfig()
    config.LOGCONFIG = deepcopy(config.LOGCONFIG)
    config.LOGCONFIG['handlers']['request']['class'] = handler_class

    logcfg = init_app(app, config)

    url = '/foo'

    @app.route(url)
    def foo():
        logging.debug('bar')
        return ''

    with app.test_request_context():
        app.test_client().get(url)

    with pytest.raises(RuntimeError) as excinfo:
        flask.request.url

    assert ('working outside of request context'
            in logconfig._compat.text_type(excinfo.value))

    logcfg.stop_listeners()

    out, err = capsys.readouterr()

    assert url in out


def test_request_context_from_record(app):
    with app.test_request_context() as ctx:
        with request_context_from_record() as test_ctx:
            assert test_ctx is ctx


@parametrize('func', [
    request_context_from_record,
])
def test_request_context_exception(func):
    with pytest.raises(FlaskLogConfigException):
        with func({}):
            pass
