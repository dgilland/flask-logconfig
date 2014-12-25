***************
Flask-LogConfig
***************

|version| |travis| |coveralls| |license|

Flask extension for configuring Python logging module.


Requirements
============


Compatibility
-------------

- Python 2.6
- Python 2.7
- Python 3.3
- Python 3.4


Dependencies
------------

- `Flask <https://github.com/mitsuhiko/flask>`_
- `logconfig <https://github.com/dgilland/logconfig>`_


Installation
============


::

    pip install Flask-LogConfig


Quickstart
==========

Use ``Flask-LogConfig`` to easily configure the Python logging module using your Flask app's ``config`` object:


.. code-block:: python

    import flask
    from flask.ext.logconfig import LogConfig

    class MyConfig(object):
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    '()': 'myapp.logging.simple_formatter_factory'
                },
                'email': {
                    '()': 'myapp.logging.email_formatter_factory'
                }
            },
            'filters': {
                'email': {
                    '()': 'myapp.logging.RequestFilter'
                }
            },
            'handlers': {
                'smtp': {
                    'class': 'logging.handlers.SMTPHandler',
                    'level': 'ERROR',
                    'formatter': 'email',
                    'filters': ['email'],
                    'mailhost': ('example.com', 587),
                    'fromaddr': 'Mailer <mailer@example.com>',
                    'toaddrs': ['admins@example.com'],
                    'subject': 'Application Error',
                    'credentials': ('mailer@example.com', 'password'),
                    'secure': ()
                },
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'stream': 'ext://sys.stderr'
                }
            },
            'loggers': {
                'myapp': {
                    'handlers': ['smtp', 'console'],
                    'level': 'DEBUG'
                }
            }
        }

        LOGGING_QUEUE = ['myapp']

    app = flask.Flask(__name__)
    app.config.from_object(MyConfig)
    logcfg = LogConfig(app)

    # or using lazy instantiation
    logcfg = LogConfig()
    logcfg.init_app(app)


Configuration
=============

Configuration of Python's logging module is specified using the standard ``dictConfig`` or ``fileConfig`` formats supported by `logging.config <https://docs.python.org/library/logging.config.html>`_. This allows Flaks apps to be configured as one would in a Django app that uses `logging <https://docs.djangoproject.com/en/1.7/topics/logging/>`__.


LOGGING
-------

The main configuration option for ``Flask-LogConfig`` is ``LOGGING``. This option can either be a ``dict`` or a pathname to a configuration file. The format of the ``dict`` or config file must follow the format supported by ``logging.config.dictConfig`` or ``loging.config.fileConfig``. See `Logging Configuration <https://docs.python.org/library/logging.config.html>`_ for more details. If using a pathname, the supported file formats are ``JSON``, ``YAML``, and ``ConfigParser``.


LOGGING_QUEUE
-------------

The purpose of ``LOGGING_QUEUE`` is to provide an easy way to utilize logging without blocking the main thread.

To set up a basic logging queue, specify the loggers you want to queuify by setting ``LOGGING_QUEUE`` to a list of the logger names (as strings). These loggers will have their handlers moved to a queue which will then be managed by a queue handler and listener, one per logger.

Each logger's queue handler will be an instance of ``flask_logconfig.FlaskQueueHandler`` which is an extension of `logging.handlers.QueueHandler <https://docs.python.org/3/library/logging.handlers.html#queuehandler>`_ (back ported to Python 2 via `logutils <https://pypi.python.org/pypi/logutils>`_). ``FlaskQueueHandler`` adds a copy of the current request context to the log record so that the queuified log handlers can access any Flask request globals outside of the normal request context (i.e. inside the listener thread) via ``flask_logconfig.request_context_from_record``. The queue listener used is an instance of `logconfig.QueueListener <https://github.com/dgilland/logconfig>`_ that extends `logging.handlers.QueueListener <https://docs.python.org/3/library/logging.handlers.html#logging.handlers.QueueListener>`_ with proper support for respecting a handler's log level (i.e. ``logging.handlers.QueueListener`` delegates all log records to a handler even if that handler's log level is set higher than the log record's while ``logconfig.QueueListener`` does not).

After the log handlers are queuified, their listener thread will be started automatically unless you specify otherwise. You can access the listeners via the ``LogConfig`` instance:


.. code-block:: python

    logcfg = LogConfig()

    # start_listeners=True by default
    logcfg.init_app(app, start_listeners=False)

    assert isinstance(logcfg, list)

    # start listeners manually
    logcfg.start_listeners()

    # stop listeners
    logcfg.stop_listeners()



Log Record Request Context
==========================

When using ``LOGGING_QUEUE``, accessing Flask's request globals from within a log handler requires using the request context that is attached to the emitted log record.

Below is an example that uses a logging ``Filter`` to attach the request environment to the log record using ``flask_logconfig.request_context_from_record``:


.. code-block:: python

    import logging
    from pprint import pformat
    from flask import request

    from flask_logconfig import request_context_from_record

    class RequestFilter(logging.Filter):
        """Impart contextual information related to Flask HTTP request."""
        def filter(self, record):
            """Attach request contextual information to log record."""
            with request_context_from_record(record):
                record.environ_info = request.environ.copy()
                record.environ_text = pformat(record.environ_info)
            return True


It's also safe to use ``request_context_from_record`` from directly inside Flask's request context:


.. code-block:: python


    with request_context_from_record():
        # do something using Flask request globals
        pass


If no request context exists (either on the log record provided or inside the actual Flask request context), then a ``flask_logconfig.FlaskLogConfigException`` will be thrown.


.. |version| image:: http://img.shields.io/pypi/v/flask-logconfig.svg?style=flat
    :target: https://pypi.python.org/pypi/flask-logconfig/

.. |travis| image:: http://img.shields.io/travis/dgilland/flask-logconfig/master.svg?style=flat
    :target: https://travis-ci.org/dgilland/flask-logconfig

.. |coveralls| image:: http://img.shields.io/coveralls/dgilland/flask-logconfig/master.svg?style=flat
    :target: https://coveralls.io/r/dgilland/flask-logconfig

.. |license| image:: http://img.shields.io/pypi/l/flask-logconfig.svg?style=flat
    :target: https://pypi.python.org/pypi/flask-logconfig/
