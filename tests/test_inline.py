
from __future__ import unicode_literals

import re

import docutils.nodes
from docutils.parsers.markdown import inline
import pytest


def test_structure():
    nodes = [docutils.nodes.Text('unchanging text')]
    assert inline.parse_text_nodes(nodes) == nodes


@pytest.mark.parametrize('original,expected', [
    ([docutils.nodes.Text('*emphatic text*')],
     [docutils.nodes.emphasis(docutils.nodes.Text('emphatic text'))]),
    ([docutils.nodes.Text('*emphatic* text')],
     [docutils.nodes.emphasis(docutils.nodes.Text('emphatic')),
      docutils.nodes.Text(' text')]),
])
def test_emphasis(original, expected):
    assert inline.parse_text_nodes(original) == expected


def test_partitioning():
    expr = re.compile(r'\*(.*)\*')
    children = [docutils.nodes.Text('hello *world* goodbye')]
    left, matched, right = inline.re_partition(children, expr)
    print(left, matched, right)
    assert len(left) == len(right) == 1
    assert len(matched) == 2
    assert len(matched[0]) == len(matched[1]) == 1
    assert left[0] == 'hello '
    assert right[0] == ' goodbye'
    assert matched[0][0] == '*world*'
    assert matched[1][0] == 'world'


@pytest.mark.parametrize('text,doctree', [
    ('This is `code` with one tick',
     '<paragraph>This is <literal>code</literal> with one tick</paragraph>'),
    ('This is ``code`` with two ticks',
     '<paragraph>This is <literal>code</literal> with two ticks</paragraph>'),
    ('This is ``invalid code` with unbalanced ticks',
     '<paragraph>This is ``invalid code` with unbalanced ticks</paragraph>'),
    ('This is ```invalid code`` with unbalanced ticks',
     '<paragraph>This is ```invalid code`` with unbalanced ticks</paragraph>'),
    ('This is `invalid code`` with unbalanced ticks',
     '<paragraph>This is `invalid code`` with unbalanced ticks</paragraph>'),
    ('This is `code` with a second `code` block',
     '<paragraph>This is <literal>code</literal> with a second '
     '<literal>code</literal> block</paragraph>'),
    ('Some `code with &amp; entities`',
     '<paragraph>Some <literal>code with &amp; entities</literal></paragraph>'),
    ('Some `code with &amp; entities`',
     '<paragraph>Some <literal>code with &amp; entities</literal></paragraph>'),
    ('Some `code with &amp; entities` also outside &quot;',
     '<paragraph>Some <literal>code with &amp; entities</literal> also outside "</paragraph>'),
])
def test_code(text, doctree):
    node = docutils.nodes.paragraph('', docutils.nodes.Text(text))
    node = inline.parse_node(node)
    assert str(node) == doctree


@pytest.mark.parametrize('text,doctree', [
    (r'This \* is escaped',
     '<paragraph>This * is escaped</paragraph>'),
])
def test_escape(text, doctree):
    node = docutils.nodes.paragraph('', docutils.nodes.Text(text))
    node = inline.parse_node(node)
    assert str(node) == doctree


@pytest.mark.parametrize('text,doctree', [
    ('&copy;', '<paragraph>\u00a9</paragraph>'),
    ('&amp;', '<paragraph>&</paragraph>'),
    ('&amp;amp;', '<paragraph>&amp;</paragraph>'),
    ('&#1234;', '<paragraph>\u04d2</paragraph>'),
    ('&#x1234;', '<paragraph>\u1234</paragraph>'),
    ('&#ff;', '<paragraph>&#ff;</paragraph>'),
    ('&#0;', '<paragraph>\ufffd</paragraph>'),
    ('&#x0;', '<paragraph>\ufffd</paragraph>'),
    ('&alpha; &beta; &gamma;', '<paragraph>\u03b1 \u03b2 \u03b3</paragraph>'),
    ('&nonexistant;', '<paragraph>&nonexistant;</paragraph>'),
])
def test_entities(text, doctree):
    node = docutils.nodes.paragraph('', docutils.nodes.Text(text))
    node = inline.parse_node(node)
    assert unicode(node) == doctree
