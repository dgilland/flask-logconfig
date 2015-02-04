Changelog
=========


- Add ``execution_time`` to log's extra data and request message data.
- Rename ``FlaskLogConfig.after_request_handler`` to ``FlaskLogConfig.after_request``. **(possible breaking change)**
- Rename ``FlaskLogConfig.get_request_msg_data`` to ``FlaskLogConfig.get_request_message_data``. **(possible breaking change)**
- Rename ``FlaskLogConfig.make_request_msg`` to ``FlaskLogConfig.make_request_message``. **(possible breaking change)**


v0.3.1 (2015-01-26)
-------------------

- Add metadata to main module:

    - ``__title__``
    - ``__summary__``
    - ``__url__``
    - ``__version__``
    - ``__author__``
    - ``__email__``
    - ``__license__``


v0.3.0 (2015-01-25)
-------------------

- Add support for logging all requests.
- Don't store any application specific state on ``LogConfig`` class. Move ``LogConfig.listeners`` access to ``LogConfig.get_listeners``. **(breaking change)**
- Make ``LogConfig.__init__`` and ``LogConfig.init_app`` accept custom queue class via ``queue_class`` argument.
- Make ``LogConfig.start_listeners()`` and ``LogConfig.stop_listeners()`` accept optional ``app`` argument to access listeners associated with that app. If no ``app`` passed in, then ``flask.current_app`` will be accessed.
- Rename supported configuration keys from ``LOGGING`` and ``LOGGING_QUEUE``to ``LOGCONFIG`` and ``LOGCONFIG_QUEUE`` respectively. **(breaking change)**


v0.2.0 (2015-01-22)
-------------------

- Make ``LogConfig.__init__`` and ``LogConfig.init_app`` accept custom handler and listener classes via ``handler_class`` and ``listener_class`` arguments.


v0.1.0 (2014-12-24)
-------------------

- First release.
