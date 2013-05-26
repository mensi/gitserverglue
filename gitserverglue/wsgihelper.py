# -*- coding: utf-8 -*-
#
# Copyright 2011 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of GitServerGlue.
#
# GitServerGlue is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GitServerGlue is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GitServerGlue.  If not, see http://www.gnu.org/licenses

from twisted.web.server import NOT_DONE_YET
import twisted.web.wsgi as twsgi


class _WSGIResponse(twsgi._WSGIResponse):
    def __init__(self, reactor, threadpool, application, request,
                 environ=None):
        twsgi._WSGIResponse.__init__(self, reactor, threadpool, application,
                                     request)

        if environ is not None:
            self.environ.update(environ)


class WSGIResource(twsgi.WSGIResource):
    def __init__(self, reactor, threadpool, application, environ=None):
        twsgi.WSGIResource.__init__(self, reactor, threadpool, application)

        self.environ = environ

    def render(self, request):
        response = _WSGIResponse(
            self._reactor, self._threadpool,
            self._application, request, self.environ)
        response.start()
        return NOT_DONE_YET

    def withEnviron(self, environ):
        """Create a new WSGIResource which will set an environ on rendering"""
        return WSGIResource(self._reactor, self._threadpool,
                            self._application, environ)
