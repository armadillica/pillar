#!/usr/bin/env python

"""Setup file for testing, not for packaging/distribution."""

import setuptools
from setuptools.command.develop import develop
from setuptools.command.install import install


def translations_compile():
    """Compile any existent translation.
    """
    from pillar import cli
    cli.translations.compile()


class PostDevelopCommand(develop):
    """Post-installation for develop mode."""
    def run(self):
        super().run()
        translations_compile()


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        super().run()
        translations_compile()


setuptools.setup(
    name='pillar',
    version='2.0',
    packages=setuptools.find_packages('.', exclude=['test']),
    install_requires=[
        'Flask>=0.12',
        'Eve>=0.7.3',
        'Flask-Cache>=0.13.1',
        'Flask-Script>=2.0.5',
        'Flask-Login>=0.3.2',
        'Flask-OAuthlib>=0.9.3',
        'Flask-WTF>=0.12',
        'algoliasearch>=1.12.0',
        'attrs>=16.2.0',
        'bugsnag>=2.3.1',
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
    entry_points = {'console_scripts': [
        'translations = pillar.cli.translations:main',
    ]},
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
    zip_safe=False,
)
