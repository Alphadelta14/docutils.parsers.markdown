
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


def slice_node(node, split):
    """Splits a node up into two sides.

    For text nodes, this will return two text nodes.

    For text elements, this will return two of the source nodes with children
    distributed on either side. Children that live on the split will be
    split further.

    Parameters
    ----------
    node : docutils.nodes.Text or docutils.nodes.TextElement
    split : int
        Location of the represented text to split at.

    Returns
    -------
    (left, right) : (type(node), type(node))
    """
    if isinstance(node, Text):
        return Text(node[:split]), Text(node[split:])
    elif isinstance(node, docutils.nodes.TextElement):
        if split < 0:
            split = len(node.astext())+split
        right = node.deepcopy()
        left = node.deepcopy()
        left.clear()
        offset = 0
        while offset < split:
            try:
                child = right.pop(0)
            except IndexError:
                break
            child_strlen = len(child.astext())
            if offset+child_strlen < split:
                left.append(child)
                offset += child_strlen
                continue
            elif offset+child_strlen != split:
                child_left, child_right = slice_node(child, split-offset)
                left.append(child_left)
                right.insert(0, child_right)
            offset += child_strlen
        return left, right
    else:
        raise ValueError('Cannot split {}'.format(repr(node)))


def slice_node_range(node, start, stop):
    node, right_ = slice_node(node, stop)
    left_, node = slice_node(node, start)
    return node


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
        if isinstance(child, (Text, docutils.nodes.Inline)) and not getattr(child, 'skip', False):
            target += child.astext()
        end = len(target)
        ranges[id(child)] = [start, end]
    match = expr.search(target)
    if match is None:
        return children, [], []
    start, end = match.span()
    left = []
    middle = [[] for group in match.regs]
    right = []
    for child in children:
        c_start, c_end = ranges[id(child)]
        if c_end < start:
            left.append(child)
        elif c_start >= end:
            right.append(child)
        else:
            if c_start < start:
                frag, right_ = slice_node(child, start-c_start)
                left.append(frag)
            if c_end > end:
                left_, frag = slice_node(child, end-c_end)
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
                frag = slice_node_range(child, g_start-c_start, g_end-c_start)
                middle[idx].append(frag)
    return left, middle, right


def match_into(children, expr_text, node_cls, group=1, skip=False):
    expr_text = expr_text.format(**EXPR_MAP)
    expr = re.compile(expr_text)
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        node = node_cls('', *middle[group])
        node.skip = skip
        children = left+[node]+right
    return children


def parse_code(children):
    children = match_into(children, r'(?<!\\)(?<!`)(``?)(?!`)(.+?)(?<!`)\1(?!`)',
                          docutils.nodes.literal, group=2, skip=True)
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


def parse_images(children):
    expr = re.compile(r'!\[([^\[\]]*)\]'
                      r'\(\s*<?([^<> ]*)>?\s*'
                      r'("[^"]*"|'+r"'[^']'*"+r'|\([^()]\))?\)')
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        attrs = {}
        description = ''.join(middle[1])
        url = ''.join(middle[2])
        title = ''.join(middle[3])[1:-1]
        if title:
            attrs['title'] = title
        attrs['alt'] = description
        attrs['uri'] = url
        node = docutils.nodes.image('', **attrs)
        node.skip = True
        children = left+[node]+right
    return children


def parse_links(children):
    expr = re.compile(r'\[([^\[\]]*)\]'
                      r'\(\s*<?([^<> ]*)>?\s*'
                      r'("[^"]*"|'+r"'[^']'*"+r'|\([^()]\))?\)')
    while True:
        left, middle, right = re_partition(children, expr)
        if not middle:
            break
        attrs = {}
        text = ''.join(middle[1])
        refuri = ''.join(middle[2])
        title = ''.join(middle[3])[1:-1]
        if refuri:
            attrs['refuri'] = refuri
        if title:
            attrs['title'] = title
        attrs['names'] = docutils.nodes.fully_normalize_name(text)
        node = docutils.nodes.target('', '', *middle[1], **attrs)
        node.skip = True
        children = left+[node]+right
    return children


def parse_emphasis_strong(children):
    def strong_emphasis(rawsource, text):
        return docutils.nodes.strong(rawsource, docutils.nodes.emphasis(rawsource, text))

    for delim, node_func in ((r'\*\*\*', strong_emphasis),
                             (r'\*\*', docutils.nodes.strong),
                             (r'__', docutils.nodes.strong),
                             (r'\*', docutils.nodes.emphasis),
                             (r'_', docutils.nodes.emphasis)):
        children = match_into(children, r'(?:^|(?<=[W\s])){delim}(.*?){delim}(?:$|(?=[\W\s]))'
                                        .format(delim=delim), node_func)
    return children


def parse_text_nodes(children):
    children = parse_code(children)
    children = parse_backslash(children)
    children = parse_entities(children)
    children = parse_images(children)
    children = parse_links(children)
    children = parse_emphasis_strong(children)
    return children


def parse_node(node):
    children = parse_text_nodes(node.children)
    node.clear()
    node += children
    return node
