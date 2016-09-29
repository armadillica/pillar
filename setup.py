#!/usr/bin/env python

"""Setup file for testing, not for packaging/distribution."""

import setuptools

setuptools.setup(
    name='pillar',
    version='2.0',
    packages=setuptools.find_packages('.', exclude=['test']),
    install_requires=[
        'Flask>0.10,<0.11',  # Flask 0.11 is incompatible with Eve 0.6.4
        'Eve>=0.6.3',
        'Flask-Cache>=0.13.1',
        'Flask-Script>=2.0.5',
        'Flask-Login>=0.3.2',
        'Flask-OAuthlib>=0.9.3',
        'Flask-WTF>=0.12',
        'algoliasearch>=1.8.0,<1.9.0',  # 1.9 Gives an issue importing some exception class.
        'attrs>=16.2.0',
        'bugsnag>=2.3.1,<3.0',  # latest version on PyPi is beta of 3.0
        'gcloud>=0.12.0',
        'google-apitools>=0.4.11',
        'MarkupSafe>=0.23',
        'Pillow>=2.8.1',
        'requests>=2.9.1',
        'rsa>=3.3',
        'zencoder>=0.6.5',
        'bcrypt>=2.0.0',
        'blinker>=1.4',
        'pillarsdk',
    ],
    tests_require=[
        'pytest>=2.9.1',
        'responses>=0.5.1',
        'pytest-cov>=2.2.1',
        'mock>=2.0.0',
    ],
    zip_safe=False,
)
