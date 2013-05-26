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

import os
import os.path
import sys

from twisted.internet import reactor
from twisted.conch.ssh import keys
from twisted.python import log

from Crypto.PublicKey import RSA

from gitserverglue import ssh, http, git
from gitserverglue.streamingweb import make_site_streaming
from gitserverglue.wsgihelper import WSGIResource

from ConfigParser import SafeConfigParser
from passlib.apache import HtpasswdFile


class TestAuthnz(object):
    def __init__(self,
                 htpasswd_file=".htpasswd",
                 perms_file=".repoperms",
                 keys_file=".rsakeys"):
        self.htpasswd = HtpasswdFile(htpasswd_file)
        self.perms_file = perms_file
        self.keys_file = keys_file

    def can_read(self, username, path_info):
        return self._check_access(username, path_info, "r")

    def can_write(self, username, path_info):
        return self._check_access(username, path_info, "w")

    def _check_access(self, username, path_info, level):
        if username is None:
            username = "anonymous"

        if path_info['repository_fs_path'] is None:
            return False

        repo = os.path.basename(path_info['repository_fs_path'])

        config = SafeConfigParser()
        config.read(self.perms_file)

        if not config.has_option(repo, username):
            return False

        return level in config.get(repo, username)

    def check_password(self, username, password):
        self.htpasswd.load_if_changed()
        return self.htpasswd.check_password(username, password)

    def check_publickey(self, username, keyblob):
        with open(self.keys_file, 'rb') as f:
            for line in f:
                try:
                    user, key = line.split(':', 1)
                    if (username == user.strip() and
                        keyblob == keys.Key.fromString(data=key.strip()
                                                       ).blob()):
                        return True
                except:
                    log.err(None, "Loading key failed")
        return False


class TestGitConfiguration(object):
    git_binary = 'git'
    git_shell_binary = 'git-shell'

    def path_lookup(self, url, protocol_hint=None):
        res = {
            'repository_base_fs_path': './',
            'repository_base_url_path': '/',
            'repository_fs_path': None
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

    keylocation = os.path.expanduser(
                    os.path.join('~', '.gitserverglue', 'key.pem'))
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
