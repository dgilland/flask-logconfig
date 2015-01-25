Changelog
=========


v0.3.0 (xxxx-xx-xx)
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
