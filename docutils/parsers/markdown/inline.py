
from __future__ import unicode_literals

try:
    from htmlentitydefs import entitydefs
except ImportError:
    from html.entities import entitydefs

    unichr = chr
import re

import docutils.nodes
from docutils.nodes import Text

EXPR_MAP = {
    'ascii': r'[ -~]',
    'before_word': r'(?:^|(?<=[.\s]))',
    'after_word': r'(?=$|[.\s])',
}


class Escaped(docutils.nodes.TextElement):
    skip = True

    def astext(self):
        return self.children[0].astext()

    def __unicode__(self):
        return docutils.nodes.reprunicode(self.children[0])

    def __str__(self):
        return str(self.children[0])


def re_partition(children, expr):
    """Splits up a list of text nodes into regex groups.

    Parameters
    ----------
    children : list(docutils.nodes.Node)
    expr : re.SRE

    Returns
    -------
    (l_children, groups, r_children) : (list(Node), list(list(Node)), list(Node))
        l_children are the children found before the entire regex match
        r_children are the children found after the entire regex
        groups are the list of groups containing matching children lists
        Note that groups[0] refers to match.groups(0) and contains the entire span
    """
    target = ''
    ranges = {}
    for child in children:
        start = len(target)
        if type(child) is Text:
            target += child.astext()
        end = len(target)
        ranges[id(child)] = [start, end]
    match = expr.search(target)
    print(expr, target)
    if match is None:
        return children, [], []
    start, end = match.span()
    left = []
    middle = [[] for group in match.regs]
    right = []
    for child in children:
        c_start = ranges[id(child)][0]
        c_end = ranges[id(child)][1]
        if c_end < start:
            left.append(child)
        elif c_start >= end:
            right.append(child)
        else:
            if c_start < start:
                child_split = start-c_start
                frag = Text(child[:child_split])
                left.append(frag)
            if c_end > end:
                child_split = end-c_end
                frag = Text(child[child_split:])
                right.append(frag)
            for idx, span in enumerate(match.regs):
                # group start/end
                g_start, g_end = span
                if g_start <= c_start <= c_end < g_end:
                    # fits perfectly into this group
                    # c = (3, 5); g = (2, 6)
                    middle[idx].append(child)
                    continue
                if c_end < g_start or c_start >= g_end:
                    # doesn't match this group
                    # c = (3, 5); g = (5, 7)
                    continue
                # c = (3, 5); g = (2, 4)
                frag = Text(child[max(g_start-c_start, 0):g_end-c_start])
                middle[idx].append(frag)
    return left, middle, right


def match_into(children, expr_text, node, group=1):
    expr_text = expr_text.format(**EXPR_MAP)
    expr = re.compile(expr_text)
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        children = left+[node('', *middle[group])]+right
    return children


def parse_code(children):
    children = match_into(children, r'(?<!\\)(?<!`)(``?)(?!`)(.+?)(?<!`)\1(?!`)',
                          docutils.nodes.literal, group=2)
    return children


def parse_backslash(children):
    children = match_into(children, r'(?:\\({ascii}))', Escaped)
    return children


def parse_entities(children):
    expr = re.compile(r'&({ents});'.format(ents='|'.join(re.escape(ent)
                                                         for ent in entitydefs)))
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        key = ''.join(middle[1])
        if key == 'amp':
            value = Escaped('', '&')
        else:
            try:
                value = Text(entitydefs[key])
            except UnicodeDecodeError:
                value = Text(entitydefs[key].decode('unicode_escape'))
        children = left+[value]+right

    # handle numeric entities now
    expr = re.compile('&#(x?)([0-9a-f]+);', re.IGNORECASE)
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        try:
            key = ''.join(middle[2])
            if middle[1][0].lower() == 'x':  # hex
                int_value = int(key, 16)
            else:
                int_value = int(key, 10)
            if not int_value:
                int_value = 0xFFFD
            value = Text(unichr(int_value))
        except ValueError:
            value = Escaped('', '&#{key};'.format(key=key))
        except UnicodeEncodeError:
            value = Text(u'\uFFFD')
        children = left+[value]+right
    return children


def parse_emphasis(children):
    children = match_into(children, r'(?:^|(?<=[.\s]))\*(.*?)\*(?:$|(?=[.\s]))',
                          docutils.nodes.emphasis)
    children = match_into(children, r'(?:^|(?<=[.\s]))_(.*?)_(?:$|(?=[.\s]))',
                          docutils.nodes.emphasis)
    return children


def parse_text_nodes(children):
    children = parse_code(children)
    children = parse_backslash(children)
    children = parse_entities(children)
    children = parse_emphasis(children)
    return children


def parse_node(node):
    children = parse_text_nodes(node.children)
    node.clear()
    node += children
    return node
