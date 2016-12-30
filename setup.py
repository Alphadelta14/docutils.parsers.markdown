#!/usr/bin/env python
"""
docutils.parsers.markdown

Author: Alpha <alpha@alphaservcomputing.solutions>

"""

from setuptools import setup, find_packages

setup(
    name='docutils.parsers.markdown',
    version='0.0.1',
    description='Docutils support for markdown',
    url='https://github.com/Alphadelta14/docutils.parsers.markdown',
    author='Alphadelta14',
    author_email='alpha@alphaservcomputing.solutions',
    license='MIT',
    scripts=[
        'bin/markdown2doctree',
    ],
    install_requires=[
        'docutils',
    ],
    packages=find_packages(),
    namespace_packages=[
        'docutils',
        'docutils.parsers',
    ],
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Plugins',
                 'License :: OSI Approved :: MIT License',
                 'Topic :: Documentation',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3'],
    keywords='docutils markdown rst sphinx',
)
