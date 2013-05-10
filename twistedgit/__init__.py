# -*- coding: utf-8 -*-
#
# Copyright 2011 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of TwistedGit.
#
# TwistedGit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TwistedGit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TwistedGit.  If not, see http://www.gnu.org/licenses

import os
import os.path
import sys

from twisted.internet import reactor
from twisted.conch.ssh import keys
from twisted.python import log

from Crypto.PublicKey import RSA

from twistedgit import ssh, http, git
from twistedgit.streamingweb import make_site_streaming
from twistedgit.wsgihelper import WSGIResource


class TestAuthnz(object):
    def can_read(self, username, path_info):
        if username is None:
            return path_info['repository_fs_path'] is not None and os.path.basename(path_info['repository_fs_path']).startswith('public_')
        else:
            return True

    def can_write(self, username, path_info):
        return True

    def check_password(self, username, password):
        return username == 'test' and password == 'test'

    def check_publickey(self, username, keyblob):
        return username == 'test' and keyblob == keys.Key.fromString(data=publicKey).blob()


class TestGitConfiguration(object):
    git_binary = 'git'
    git_shell_binary = 'git-shell'

    def path_lookup(self, url, protocol_hint=None):
        res = {
            'repository_base_fs_path': './',
            'repository_base_url_path': '/',
            'repository_fs_path' : None
        }

        pathparts = url.strip('/').split('/')

        if len(pathparts) > 0 and pathparts[0].endswith('.git'):
            p = os.path.join('./', pathparts[0])
            if os.path.exists(p):
                res['repository_fs_path'] = p
                res['repository_clone_urls'] = {
                    'http': 'http://localhost:8080/' + pathparts[0],
                    'git': 'git://localhost/' + pathparts[0],
                    'ssh': 'ssh://localhost:5522/' + pathparts[0]
                }


        return res


def find_git_viewer():
    """Tries to find a known git viewer"""
    # pyggi - https://www.0xdeadbeef.ch/pyggi/pyggi.git/
    # not to be confused with PyGGI from PyPI
    try:
        from pyggi.lib.config import config

        config.add_section('general')
        config.set('general', 'preserve_daemon_export', "false")
        config.set('general', 'name', "pyggi")

        config.add_section('clone')

        config.add_section('modules')
        config.set('modules', 'pyggi.repositories.frontend', '/')
        config.set('modules', 'pyggi.base.base', '/')

        from pyggi import create_app

        return WSGIResource(reactor, reactor.getThreadPool(), create_app())

    except:
        pass


def main():
    log.startLogging(sys.stderr)

    keylocation = os.path.expanduser(os.path.join('~', '.twistedgit', 'key.pem'))
    key = None

    if os.path.exists(keylocation):
        try:
            key = keys.Key.fromFile(keylocation)
        except:
            pass

    if key is None:
        rsakey = RSA.generate(2048)
        key = keys.Key(rsakey)

        try:
            if not os.path.exists(os.path.dirname(keylocation)):
                os.mkdir(os.path.dirname(keylocation))
            f = open(keylocation, 'wb')
            f.write(rsakey.exportKey('PEM'))
            f.close()
        except:
            log.err(None, "Failed to write key to " + keylocation)

    ssh_factory = ssh.create_factory(
        public_keys={'ssh-rsa': key},
        private_keys={'ssh-rsa': key},
        authnz=TestAuthnz(),
        git_configuration=TestGitConfiguration()
    )

    http_factory = http.create_factory(
        authnz=TestAuthnz(),
        git_configuration=TestGitConfiguration(),
        git_viewer=find_git_viewer()
    )

    git_factory = git.create_factory(
        authnz=TestAuthnz(),
        git_configuration=TestGitConfiguration()
    )

    reactor.listenTCP(5522, ssh_factory)
    reactor.listenTCP(8080, make_site_streaming(http_factory))
    reactor.listenTCP(9418, git_factory)
    reactor.run()
