#!/usr/bin/env python

"""Setup file for testing, not for packaging/distribution."""

import setuptools

setuptools.setup(
    name='pillar',
    version='1.0',
    packages=setuptools.find_packages('pillar', exclude=['manage']),
    package_dir={'': 'pillar'},  # tell setuptools packages are under src
    tests_require=['pytest'],
    zip_safe=False,
)
