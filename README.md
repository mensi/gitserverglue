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

TwistedGit will install a command you can use to serve git repositories in the current directory.
You need to create three files to control access:

 * `.htaccess` is a apache-style htaccess file containing users and their passwords.
 * `.repoperms` is an ini-style config file. You need to create a section for each repository
   with `user = rw` mappings. The user `anonymous` is used when no user is given. Example:
   
	       [test.git]
	       myuser = rw
	       otheruser = r
	       anonymous = r
       
       
 * `.rsakeys` should contain lines of the form `username: rsakey` where `rsakey` is the contents of the `.pub` file
   `ssh-keygen` generates.
   
You can then invoke `twistedgit`:

	$ twistedgit 
	2013-05-11 13:48:53+0200 [-] Log opened.
	2013-05-11 13:48:53+0200 [-] Registering PasswordChecker
	2013-05-11 13:48:53+0200 [-] Registering PublicKeyChecker
	2013-05-11 13:48:53+0200 [-] Registering PasswordChecker
	2013-05-11 13:48:53+0200 [-] GitSSHFactory starting on 5522
	2013-05-11 13:48:53+0200 [-] Starting factory <twistedgit.ssh.GitSSHFactory instance at 0x204c050>
	2013-05-11 13:48:53+0200 [-] Site starting on 8080
	2013-05-11 13:48:53+0200 [-] Starting factory <twisted.web.server.Site instance at 0x264a050>
	2013-05-11 13:48:53+0200 [-] GitFactory starting on 9418
	2013-05-11 13:48:53+0200 [-] Starting factory <twistedgit.git.GitFactory instance at 0x264a098>
	
	
The implementation (in `twistedgit/__init__.py`) demonstrates the basic usage. The class `TestAuthnz` handles 
authentication (`check_password`, `check_publickey`) and authorization (`can_read`, `can_write`) while 
`TestGitConfiguration` maps virtual URLs to filesystem paths. 