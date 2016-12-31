
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
