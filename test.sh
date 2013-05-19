#!/bin/bash

VENV=`mktemp -d`
PKG=`ls dist/ | sort -n | head -1`

if [ ! -e dist/$PKG ]
then
	echo "Unable to find package"
	exit 1
fi

set -e

virtualenv --system-site-packages $VENV
pip install -E $VENV dist/$PKG
cd $VENV
source bin/activate

git init --bare test.git
htpasswd -cb .htpasswd test test
echo -e "[test.git]\ntest = rw\nanonymous = r" > .repoperms
ssh-keygen -f test_key -N ""
echo -n "test: " > .rsakeys
cat test_key.pub >> .rsakeys

twistedgit &
TWISTEDGIT_PID=$!

# wait a bit to give twistedgit a chance to start
sleep 5

git clone http://test:test@localhost:8080/test.git test_http
echo "hello world" > test_http/test.txt
cd test_http
git add test.txt
git commit -m "Test Commit"
git push origin master
cd ..

git clone git://localhost/test.git test_git
if [ ! -e test_git/test.txt ]
then
	echo "[git://] Comitted file missing!!!"
	kill $TWISTEDGIT_PID
	exit 1
fi

ssh-agent bash -c 'ssh-add test_key; git clone ssh://test@localhost:5522/test.git test_ssh'
if [ ! -e test_ssh/test.txt ]
then
	echo "[ssh://] Comitted file missing!!!"
	kill $TWISTEDGIT_PID
	exit 1
fi
echo "hi tester" >> test_ssh/test.txt
cd test_ssh
git add test.txt
git commit -m "foobar"
ssh-agent bash -c 'ssh-add ../test_key; git push'
cd ..

kill $TWISTEDGIT_PID
deactivate
rm -rf $VENV

echo ""
echo "Congrats, test.sh reached its end ;)"
