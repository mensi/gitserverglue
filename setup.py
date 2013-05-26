#!/usr/bin/env python
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

from setuptools import setup, find_packages

setup(name='GitServerGlue',
      install_requires=['twisted', 'pycrypto', 'passlib', 'pyasn1'],
      description=(
                   'Twisted-based implementation of the '
                   'network protocols supported by git'
                   ' (git://, ssh:// and http://)'
      ),
      keywords='git ssh http',
      version='0.3',
      obsoletes=['TwistedGit'],
      url='https://github.com/mensi/gitserverglue',
      license='GPL',
      author='Manuel Stocker',
      author_email='mensi@mensi.ch',
      long_description=(
                        'Twisted-based implementation of the '
                        'network protocols supported by git'
                        ' (git://, ssh:// and http://)'
                        ),
      packages=find_packages(),
      zip_safe=True,
      entry_points={'console_scripts': ['gitserverglue = gitserverglue:main']})
