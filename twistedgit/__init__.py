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

import os.path

from twisted.internet import reactor
from twisted.conch.ssh import keys
from twisted.python import log

from twistedgit import ssh

publicKey = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCW+fhJvtLJKFsrPvQa2cT/lHq7fbczM2EgXc/qbk37s8FmiLpRftA9U4yy9uqeSdGhi4yeqvLN95Y39bzAsp/H7hM0p9yQxclFe5dZFKkvNEeXsISV4U5qrB+gQiJDuQiSVw9rhTp8BgG+JgAQ9Dk3jSYGXVz7L/33XhF2ZKxCF1CwFevzVDO6GumePtPmxvOhWAJPlvpbIZz2w3Rs/bsgfEeT2QGDjPBrwOXYNRmIHcGbfBADK7fSSdSgwHkSUAY+03tsUh9eo0oljGWapGp6TfJMiXclwn9gSPSva5nXo3wif6OC4JD4XidHu/XdFXKVMEgo1yPQWZSqQopYEA1d'
privateKey = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAlvn4Sb7SyShbKz70GtnE/5R6u323MzNhIF3P6m5N+7PBZoi6
UX7QPVOMsvbqnknRoYuMnqryzfeWN/W8wLKfx+4TNKfckMXJRXuXWRSpLzRHl7CE
leFOaqwfoEIiQ7kIklcPa4U6fAYBviYAEPQ5N40mBl1c+y/9914RdmSsQhdQsBXr
81Qzuhrpnj7T5sbzoVgCT5b6WyGc9sN0bP27IHxHk9kBg4zwa8Dl2DUZiB3Bm3wQ
Ayu30knUoMB5ElAGPtN7bFIfXqNKJYxlmqRqek3yTIl3JcJ/YEj0r2uZ16N8In+j
guCQ+F4nR7v13RVylTBIKNcj0FmUqkKKWBANXQIDAQABAoIBACkTHO/DUMmVhyg+
2l6rvKLkHHgB/eOaKOSLYVOgaur9vrJMpJQjcjgdEPxnnPEvmC7hLoLEc4aBw4a5
/n5Wmo3kQaljuehRRy72Lvj3XAgRqyCjz46PW6w94+TP2U6fequFsBZKitzPLY4z
/HSgXSi16BB3OiLErc2s9AdH4G2iSzxN/o+H/mUuTVUqsus1A8tB7O8ArvhQWm8g
Y/KWOW/JppHUMEQzxsK87Gr0lwrUrmtWwp0yGPYcaueHiLIBWzi7UnGn+mxBaZrQ
mRBgEDN0SucU2/7nRdClnZo6gBfNxN57/LRdENTl253ljht6hx5OZcGZOI/6iHpk
QHwHTekCgYEAyL9z63CKO28TPLC6nhv65X/Ox8HKmBLdlBCqjrEuyEG9hQ01xb+U
Nek8T6I2MidElFVXHMAIkliDGDNkK3FkGBTprdsDnUM5D391E6d/GSX8tYALE3eA
PBWocBfYBU8JmOrbCemfVo1zPQz6+cR3iA038YeCshNIUWylltvM438CgYEAwIeo
0urRWdLCQyz6Qkjqy5fKhn5Tfc5oATXi3irZbflR+thD7MNeMiHALxDoyvVIk1ub
URsKP2cmFgyrLpCcQWi8PjvXxJSY7Dkcv8XuYFrFcdEezuiIjGcXp9QUMWce44eT
Nb/Sve+S85gmJmEkuj+HBorU271PZZJBn25AjSMCgYB+kj/bXXy6loERjfhMAiZC
F0BgMG61TYfJeGyhRVPSzahZwId75BvlleYB66uyGZIi2F/xb5637vjRBG4O+hJ7
IIxpoqJ3wE+01s8RklUPnSTlpxLUtk7zE1C9RDtetYO+l619ZYCiSNM01f9UBay7
6mGwdplP/9pkBFWvdWyMrwKBgCdjmcaNBAe8dsIHkau9/0tn4qdhcPNsJxsYSzHo
0lMNjxgi5sKptbvL6+W1L+tWA2MiesQ9I/uUvtYEAYGlVFKNevXAiIRPYnnxtVAG
zp4n8/01K3hpWoZfERfk67yvvEIQmq2EcTkqqoXruuJfPYRdOuK7xJCwSm4dXg+g
HtTBAoGAQIZZldU0MScmhPsjfiOhqBPb3nmF5MwzGdVB9geDSubStWKE3ITVoIVc
gFSLuSSutKb7CMKC+Fj9WUuUqrbHUGEOtEM4iCRS0fo5Txie3JonJRvbdDbiZPly
W1P00tKVMReVahFqwehet6qt56HXV143CpdCM/v3O/0+vjtPSZA=
-----END RSA PRIVATE KEY-----"""

class TestAuthnz(object):
    def can_read(self, username, gitpath):
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
        return os.path.join('./', virtual_path.lstrip('/'))

def main():
    log.startLogging(sys.stderr)

    ssh_factory = ssh.create_factory(
        public_keys={'ssh-rsa': keys.Key.fromString(data=publicKey)},
        private_keys={'ssh-rsa': keys.Key.fromString(data=privateKey)},
        authnz=TestAuthnz(),
        git_configuration=TestGitConfiguration()
    )

    reactor.listenTCP(5522, ssh_factory())
    reactor.run()
