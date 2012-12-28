TwistedGit
==========

TwistedGit allows you to build a service handling git over ssh. You can define your own 
virtual path to actual path mapping as well as perform your own user authentication. Both 
authentication by password as well as by public key are supported.

Installation
------------

	$ pip install twistedgit

Usage
-----

TwistedGit will install a command you can use to serve the current directory to user test/test with read and write permissions:

	$ twistedgit 
	2012-12-29 00:50:30+0100 [-] Log opened.
	2012-12-29 00:50:30+0100 [-] Registering PasswordChecker
	2012-12-29 00:50:30+0100 [-] Registering PublicKeyChecker
	2012-12-29 00:50:30+0100 [-] GitSSHFactory starting on 5522
	
See twistedgit/__init__.py for the implementation.