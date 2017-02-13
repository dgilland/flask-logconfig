
from copy import deepcopy
import logging

import pytest
import mock
import flask
import logconfig
from logutils.testing import TestHandler, Matcher

from flask_logconfig import (
    LogConfig,
    FlaskQueueHandler,
    FlaskLogConfigException,
    request_context_from_record
)


parametrize = pytest.mark.parametrize


test_logger = logging.getLogger('tests')
test_matcher = Matcher()


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


class UrlHandlerConfig(object):
    LOGCONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'url': {
                '()': 'tests.test_flask_logconfig.url_formatter_factory'
            }
        },
        'handlers': {
            'test_handler': {
                'class': 'tests.test_flask_logconfig.TestHandler',
                'level': 'DEBUG',
                'formatter': 'url',
                'matcher': test_matcher
            }
        },
        'root': {
            'handlers': ['test_handler'],
            'level': 'DEBUG'
        }
    }
    LOGCONFIG_QUEUE = ['']


class RequestsConfig(object):
    LOGCONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'test_handler': {
                'class': 'tests.test_flask_logconfig.TestHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'matcher': test_matcher
            }
        },
        'loggers': {
            'tests': {
                'handlers': ['test_handler'],
                'level': 'DEBUG'
            },
            'flask_logconfig': {
                'handlers': ['test_handler'],
                'level': 'DEBUG'
            }
        }
    }

    LOGCONFIG_REQUESTS_ENABLED = True
    LOGCONFIG_REQUESTS_LOGGER = 'tests'


class UrlFormatter(logging.Formatter):
    def format(self, record):
        with request_context_from_record(record):
            return flask.request.url


def url_formatter_factory():
    return UrlFormatter()


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

    with app.app_context():
        assert len(logcfg.get_listeners()) == len(names)

        for name in names:
            logger = logging.getLogger(name)
            assert len(logger.handlers) == 1
            assert isinstance(logger.handlers[0], FlaskQueueHandler)
            assert len(logcfg.get_listeners()[name].handlers) == len(handlers)

        logcfg.stop_listeners()


def test_logconfig_queue_request_context(app):
    config = UrlHandlerConfig()
    config.LOGCONFIG = deepcopy(config.LOGCONFIG)

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
            in logconfig._compat.text_type(excinfo.value).lower())

    with app.app_context():
        logcfg.stop_listeners()
        handler = logcfg.get_listeners()[''].handlers[0]

    assert url in handler.formatted[0]


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


@parametrize('level', [
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
])
def test_logconfig_requests_logging_level(app, level):
    config = RequestsConfig()
    config.LOGCONFIG_REQUESTS_LEVEL = getattr(logging, level)

    init_app(app, config)

    with app.test_request_context():
        app.test_client().get('/')

    handler = test_logger.handlers[0]
    message = handler.formatted[0]
    assert message == 'tests - {level} - GET / - 404'.format(level=level)


@parametrize('is_enabled', [
    True,
    False
])
def test_logconfig_requests_logging_enabled(app, is_enabled):
    config = RequestsConfig()
    config.LOGCONFIG_REQUESTS_ENABLED = is_enabled
    init_app(app, config)

    with app.test_request_context():
        app.test_client().get('/')

    handler = test_logger.handlers[0]

    assert bool(handler.buffer) == is_enabled


@parametrize('logger', [
    None,
    'tests'
])
def test_logconfig_requests_logging_logger(app, logger):
    config = RequestsConfig()
    config.LOGCONFIG_REQUESTS_LOGGER = logger
    config.LOGGER_NAME = 'flask_logconfig'
    init_app(app, config)

    with app.test_request_context():
        app.test_client().get('/')

    # If logger name is None, the default app logger will be used.
    if logger is None:
        logger = config.LOGGER_NAME

    handler = logging.getLogger(logger).handlers[0]
    message = handler.formatted[0]

    assert message == '{logger} - DEBUG - GET / - 404'.format(logger=logger)


@parametrize('key', [
    'method',
    'path',
    'base_url',
    'url',
    'remote_addr',
    'user_agent',
    'status_code',
    'status',
    'execution_time',
    'session',
    'SERVER_PORT',
    'SERVER_PROTOCOL',
    'SCRIPT_NAME',
    'REQUEST_METHOD',
    'HTTP_HOST',
    'PATH_INFO',
    'QUERY_STRING',
    'CONTENT_LENGTH',
    'SERVER_NAME',
    'CONTENT_TYPE'
])
def test_logconfig_requests_logging_message_format(app, key):
    config = RequestsConfig()
    config.LOGCONFIG_REQUESTS_MSG_FORMAT = '{{{0}}}'.format(key)

    logcfg = init_app(app, config)

    data = {}

    def after_request(response):
        data.update(logcfg.get_request_message_data(response))
        return response

    app.after_request(after_request)

    with app.test_request_context():
        app.test_client().get('/')

    handler = test_logger.handlers[0]

    # In case stored value is a subclass of dict, convert to proper dict.
    if isinstance(data[key], dict):
        data[key] = dict(data[key])

    assert key in data
    assert handler.matches(msg='{0}'.format(data[key]))


def test_logconfig_requests_logging_message_xformat_session(app):
    config = RequestsConfig()
    config.LOGCONFIG_REQUESTS_MSG_FORMAT = '{session[foo]} {session[bar]}'

    logcfg = init_app(app, config)

    data = {}

    def after_request(response):
        data.update(logcfg.get_request_message_data(response))
        return response

    app.after_request(after_request)

    with app.test_request_context():
        app.test_client().get('/')

    handler = test_logger.handlers[0]

    assert 'session' in data
    assert handler.matches(msg='None None')
