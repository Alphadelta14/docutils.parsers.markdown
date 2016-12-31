
import docutils.nodes


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
        if type(child) is docutils.nodes.Text:
            target += child.astext()
        end = len(target)
        ranges[child] = [start, end]
    match = expr.search(target)
    if match is None:
        return children, [], []
    start, end = match.span()
    left = []
    middle = [[] for group in match.regs]
    right = []
    for child in children:
        c_start = ranges[child][0]
        c_end = ranges[child][1]
        if c_end < start:
            left.append(child)
        elif c_start >= end:
            right.append(child)
        else:
            if c_start < start:
                child_split = start-c_start
                frag = docutils.nodes.Text(child[:child_split])
                left.append(frag)
            if c_end >= end:
                child_split = end-c_end
                frag = docutils.nodes.Text(child[child_split:])
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
                frag = docutils.nodes.Text(child[max(g_start-c_start, 0):g_end-c_start])
                middle[idx].append(frag)
    return left, middle, right


def parse_text_nodes(children):
    raise NotImplementedError()
    return children


def parse_node(node):
    return parse_text_nodes(node.children)
