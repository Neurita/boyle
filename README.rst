.. -*- mode: rst -*-

boyle
=====

Medical Image Conversion and Input/Output Tools

Named after Robert Boyle (1627-1691), known as the first modern chemist, although he believed in the transmutation of metals to be a possibility following the alchemical tradition.

.. image:: https://secure.travis-ci.org/alexsavio/boyle.png?branch=master
    :target: https://travis-ci.org/alexsavio/boyle
.. image:: https://coveralls.io/repos/alexsavio/boyle/badge.png
    :target: https://coveralls.io/r/alexsavio/boyle


Dependencies
============

Please see the requirements.txt file.

Install
=======

Before installing it, you need all the requirements installed.
These are listed in the requirements.txt files.
The best way to install them is running the following command:

    for r in \`cat boyle/requirements.txt\`; do pip install $r; done

This package uses distutils, which is the default way of installing
python modules. To install in your home directory, use::

    python setup.py install --user

To install for all users on Unix/Linux::

    python setup.py build
    sudo python setup.py install


Development
===========

Code
----

Github
~~~~~~

You can check the latest sources with the command::

    git clone https://www.github.com/Neurita/boyle.git

or if you have write privileges::

    git clone git@github.com:Neurita/boyle.git

If you are going to create patches for this project, create a branch for it 
from the master branch.

The stable releases are tagged in the repository.


Testing
-------

TODO
