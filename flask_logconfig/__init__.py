"""
"""

import logging
import contextlib

import logconfig

from flask import current_app, request, _request_ctx_stack, has_request_context


class FlaskLogConfigException(Exception):
    """Base exception class for Flask-LogConfig."""
    pass


class FlaskQueueHandler(logconfig.QueueHandler):
    """Extend QueueHandler to attach Flask request context to record since
    request context won't be available inside listener thread.
    """
    def prepare(self, record):
        """Return a prepared log record. Attach a copy of the current Flask
        request context for use inside threaded handlers.
        """
        record = logconfig.QueueHandler.prepare(self, record)
        record.request_context = copy_current_request_context()
        return record


class LogConfig(object):
    """Flask extension for configuring Python's logging module from
    application's config object.
    """
    default_handler_class = FlaskQueueHandler
    default_listener_class = logconfig.QueueListener

    def __init__(self,
                 app=None,
                 start_listeners=True,
                 handler_class=None,
                 listener_class=None):
        self.app = app
        self.handler_class = handler_class
        self.listener_class = listener_class

        if app is not None:  # pragma: no cover
            self.init_app(app, start_listeners=start_listeners)

    def init_app(self,
                 app,
                 start_listeners=True,
                 handler_class=None,
                 listener_class=None):
        """Initialize extension on Flask application."""
        app.config.setdefault('LOGCONFIG', None)
        app.config.setdefault('LOGCONFIG_QUEUE', [])

        if not hasattr(app, 'extensions'):  # pragma: no cover
            app.extensions = {}

        app.extensions['logconfig'] = {
            'listeners': {}
        }

        handler_class = handler_class or self.handler_class
        listener_class = listener_class or self.listener_class

        if not handler_class:
            handler_class = self.default_handler_class

        if not listener_class:
            listener_class = self.default_listener_class

        if app.config['LOGCONFIG']:
            self.setup_logging(app)

        if app.config['LOGCONFIG_QUEUE']:
            self.setup_queue(app,
                             start_listeners,
                             listener_class,
                             handler_class)

    def setup_logging(self, app):
        """Setup logging configuration for application."""
        # NOTE: app.logger clears all attached loggers from
        # app.config['LOGGER_NAME'] but ONLY AFTER FIRST ACCESS! Therefore,
        # we access it here so that whatever logging configuration is being
        # loaded won't be lost.
        app.logger
        logconfig.from_autodetect(app.config['LOGCONFIG'])

    def setup_queue(self, app, start_listeners, listener_class, handler_class):
        """Setup unified logging queue for application."""
        # Create one queue for all queued loggers.
        queue = logconfig.Queue(-1)

        for name in app.config['LOGCONFIG_QUEUE']:
            # Use a separate listener for each logger. This will result in
            # a separate thread for each logger but it avoids issues where
            # a listener emits the same record to a handler multiple times.
            listener = listener_class(queue)
            handler = handler_class(queue)
            logconfig.queuify_logger(name, handler, listener)

            self.add_listener(app, name, listener)

        if start_listeners:
            self.start_listeners(app)

    def get_app(self, app=None):
        """Look up and return application."""
        if app is not None:
            return app

        if self.app is not None:  # pragma: no cover
            return app

        return current_app

    def get_state(self, app=None):
        """Return stored state for application."""
        app = self.get_app(app)
        return app.extensions['logconfig']

    def get_listeners(self, app=None):
        """Return listeners associated with application."""
        return self.get_state(app)['listeners']

    def add_listener(self, app, name, listener):
        """Add `listener` indexed by `name` to application."""
        self.get_listeners(app)[name] = listener

    def start_listeners(self, app=None):
        """Start all queue listeners for application."""
        for listener in self.get_listeners(app).values():
            listener.start()

    def stop_listeners(self, app=None):
        """Stop all queue listeners for application."""
        for listener in self.get_listeners(app).values():
            listener.stop()


def copy_current_request_context():
    """Return a copy of the current request context which can then be used
    in queued handler processing.
    """
    top = _request_ctx_stack.top
    if top is None:  # pragma: no cover
        raise RuntimeError(
            'This function can only be used at local scopes '
            'when a request context is on the stack. For instance within '
            'view functions.')
    return top.copy()


@contextlib.contextmanager
def request_context_from_record(record=None):
    """Context manager for Flask request context attached to log record or if
    one doesn't exist, then from top of request context stack.

    Raises:
        FlaskLogConfigException: If no request context exists on `record` or
            stack.
    """
    if hasattr(record, 'request_context'):
        with record.request_context as ctx:
            yield ctx
    elif has_request_context():
        with _request_ctx_stack.top as ctx:
            yield ctx
    else:
        raise FlaskLogConfigException('No request context found on log record')
