"""Docutils reference via filename.

Instead of patching docutils.parsers._parser_aliases, this md package will
make it possible to invoke ``docutils.parsers.get_parser_class('md')``
directly.
"""
from docutils.parsers.markdown.parser import Parser

__all__ = ['Parser']
