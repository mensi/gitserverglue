TwistedGit
==========

TwistedGit implements the `git://`, `ssh://` and `http(s)://` protocols in python using 
[Twisted](http://twistedmatrix.com). You can implement your custom virtual path to 
filesystem mapping as well as implement custom authentication and authorization. For 
`ssh://` both password- and key-based logins are supported.

Since TwistedGit uses `twisted.conch` to run a custom SSH daemon, you do not need to
create system user accounts nor modify/setup custom entries in `.ssh/authorized_keys`.

Installation
------------

You can get TwistedGit from PyPI

	$ pip install twistedgit
	
or alternatively checkout the github repository and run 

	$ python setup.py install

Usage
-----

TwistedGit will install a command you can use to serve the current directory to user test/test with read and write permissions:

	$ twistedgit 
	2012-12-29 00:50:30+0100 [-] Log opened.
	2012-12-29 00:50:30+0100 [-] Registering PasswordChecker
	2012-12-29 00:50:30+0100 [-] Registering PublicKeyChecker
	2012-12-29 00:50:30+0100 [-] GitSSHFactory starting on 5522
	
The implementation (in `twistedgit/__init__.py`) demonstrates the basic usage. The class `TestAuthnz` handles 
authentication (`check_password`, `check_publickey`) and authorization (`can_read`, `can_write`) while 
`TestGitConfiguration` maps virtual URLs to filesystem paths. `split_path` is only relevant for HTTP(S) and 
splits the URL into virtual repository path and rest. 