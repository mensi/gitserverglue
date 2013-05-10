from zope.interface import implements

from twisted.web.resource import IResource
from twisted.web.server import NOT_DONE_YET
from twisted.python import log
import twisted.web.wsgi as twsgi

class _WSGIResponse(twsgi._WSGIResponse):
    def __init__(self, reactor, threadpool, application, request, environ=None):
        twsgi._WSGIResponse.__init__(self, reactor, threadpool, application, request)

        if environ is not None:
            self.environ.update(environ)

        log.msg("ENV: %r" % self.environ)

class WSGIResource(twsgi.WSGIResource):
    def __init__(self, reactor, threadpool, application, environ=None):
        twsgi.WSGIResource.__init__(self, reactor, threadpool, application)

        self.environ = environ

    def render(self, request):
        response = _WSGIResponse(
            self._reactor, self._threadpool, self._application, request, self.environ)
        response.start()
        return NOT_DONE_YET

    def withEnviron(self, environ):
        """Returns a new WSGIResource which will set the environ on render calls"""
        return WSGIResource(self._reactor, self._threadpool, self._application, environ)
