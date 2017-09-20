# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

if __name__ == '__main__':

    with open('README.rst') as f:
        readme = f.read()

    with open('LICENSE') as f:
        license = f.read()

    setup(
        name='rinpy',
        version='0.1.0',
        description='Package for reading and handling multi GNSS data',
        long_description=readme,
        author='Joakim Strandberg',
        author_email='joakim@jstrandberg.se',
        license=license,
        packages=find_packages(exclude=('data', 'tests', 'docs'))
    )
