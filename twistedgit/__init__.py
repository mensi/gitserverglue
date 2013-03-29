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


class TestAuthnz(object):
    def can_read(self, username, gitpath):
        if username is None:
            return os.path.basename(gitpath).startswith('public_')
        else:
            return True
    
    def can_write(self, username, gitpath):
        return True

    def check_password(self, username, password):
        return username == 'test' and password == 'test'

    def check_publickey(self, username, keyblob):
        return username == 'test' and keyblob == keys.Key.fromString(data=publicKey).blob()


class TestGitConfiguration(object):
    git_binary = 'git'
    git_shell_binary = 'git-shell'

    def translate_path(self, virtual_path):
        pathparts = virtual_path.lstrip('/').split('/')
        realpath = os.path.join('./', pathparts[0])
        return realpath if os.path.exists(realpath) else None
    
    def split_path(self, virtual_path):
        pathparts = virtual_path.lstrip('/').split('/')
        return '/' + pathparts[0], '/' + '/'.join(pathparts[1:])


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
        git_configuration=TestGitConfiguration()
    )
    
    git_factory = git.create_factory(
        authnz=TestAuthnz(),
        git_configuration=TestGitConfiguration()
    )

    reactor.listenTCP(5522, ssh_factory)
    reactor.listenTCP(8080, http_factory)
    reactor.listenTCP(9418, git_factory)
    reactor.run()
