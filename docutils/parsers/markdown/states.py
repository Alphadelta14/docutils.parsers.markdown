"""Markdown StateMachine and States

>>> state_machine = MarkdownStateMachine.create()
"""

import docutils.nodes
from docutils.statemachine import StateMachine, State,\
    TransitionCorrection, TransitionMethodNotFound

__all__ = ['MarkdownStateMachine']

state_classes = []


def state(cls):
    """Wraps classes to track that they are states.
    """
    state_classes.append(cls)
    return cls


def indent(line, indent=0, lazy=False, indent_chars=None):
    if indent_chars is not None:
        if line.strip('\t ').startswith(indent_chars):
            line = line.replace(indent_chars, ' ', 1)
    if not line.strip('\t '):
        return ''
    if not indent:
        return line
    while '\t' in line[:indent]:
        line = line[:indent].expandtabs(4)+line[indent:]
    if not lazy and line[:indent].strip(' '):
        raise EOFError('Unindented')
    return line


class MarkdownStateMachine(StateMachine):
    """Markdown master StateMachine
    """
    def __init__(self, state_classes, initial_state, debug=False, indent=0, indent_chars=None):
        StateMachine.__init__(self, state_classes, initial_state, debug)
        self.indent = 0
        self.indent_chars = indent_chars
        self.lazy = False

    @classmethod
    def create(cls):
        inst = cls(initial_state='Body', state_classes=state_classes)
        return inst

    def run(self, input_lines, input_offset=0, context=None,
            input_source=None, initial_state=None):
        """Runs this state machine.

        Parameters:

        - `input_lines`: list(str)
        - `input_offset` : int, optional
        - `context` : `docutils.nodes.document`
        - `input_source` : str, optional
        - `initial_state` : str
        """
        return StateMachine.run(self, input_lines, input_offset, context,
                                input_source, initial_state)

    def next_line(self, nth):
        line = StateMachine.next_line(self, nth)
        self.line = indent(line, self.indent, self.lazy, self.indent_chars)
        return self.line


class MarkdownBaseState(State):
    nested_sm_kwargs = {
        'state_classes': state_classes,
        'initial_state': 'Body',
    }
    patterns = {
        'ulist': r'\s{0,3}([*+-]) ',
        'olist': r'\s{0,3}(\d+)([.)]) ',
        'olist_only_one': r'(1)([.)]) ',
        'section': r'\s{0,3}(#{1,6})([^#].*)',
        'code_block': r'    ',
        'fence': r'\s{0,3}(`{3,}|~{3,})',
        'block_quote': r'\s{0,3}>',
        'thematic_break': r'\s{0,3}([*_-])\s*(\1\s*){2,}$',
        'paragraph': r'.',
        'blank': r'[\t ]*$',
    }

    def make_transition(self, name, next_state):
        if next_state is None:
            next_state = self.__class__.__name__
        try:
            return MarkdownBaseState.make_transition(self, name, next_state)
        except TransitionMethodNotFound:
            return self.patterns[name], self.raise_eof, next_state

    def raise_eof(self, match, context, next_state):
        raise EOFError

    def enter(self, context, next_state, nth=0, indent=0, indent_chars=None):
        """Enters a nested statemachine.

        Parameters:

        - `context`: `docutils.nodes.Node`
        - `next_state` : str
        """
        sm_kwargs = self.nested_sm_kwargs.copy()
        input_offset = self.state_machine.abs_line_offset()
        ofs = self.state_machine.line_offset+nth
        self.state_machine.next_line(nth)
        input_lines = self.state_machine.input_lines[ofs:]
        sm_kwargs['indent'] = self.state_machine.indent+indent
        sm_kwargs['indent_chars'] = indent_chars
        substate_machine = self.nested_sm(**sm_kwargs)
        results = substate_machine.run(
            input_lines, input_offset,
            context=context, initial_state=next_state
        )
        self.state_machine.goto_line(substate_machine.abs_line_offset())
        return results


@state
class Section(MarkdownBaseState):
    initial_transitions = (
        'thematic_break',
        'section',
        'code_block',
        'fence',
        'block_quote',
        'ulist',
        'olist',
        'blank',
        'paragraph',
    )

    def thematic_break(self, match, context, next_state):
        """Horizontal rule <hr>
        """
        node = docutils.nodes.transition()
        context.append(node)
        return context, next_state, []

    def section(self, match, context, next_state):
        level = match.group(1).count('#')
        supersection = context
        # Find the node that is actually a true section or root Body
        while not hasattr(supersection, 'level'):
            supersection = supersection.parent
        if level <= supersection.level:
            raise EOFError()
        trans_context = context
        while level > supersection.level:
            subcontext = docutils.nodes.section()
            subcontext.level = level
            trans_context.append(subcontext)
            level -= 1
            trans_context = subcontext
        header = docutils.nodes.title(text=match.group(2).lstrip())
        subcontext.append(header)
        return context, next_state, self.enter(subcontext, 'Section', nth=1)

    def code_block(self, match, context, next_state):
        node = docutils.nodes.literal_block()
        node.opening = None
        return context, next_state, self.enter(node, 'Code', indent=4)

    def fence(self, match, context, next_state):
        opening = match.group(1)
        lang = match.string[match.end(1):].strip()
        node = docutils.nodes.literal_block()
        if lang:
            lang = lang.split(' ')[0]
            node['classes'].append(lang)
        node.opening = opening
        return context, next_state, self.enter(node, 'Code', nth=1)

    def block_quote(self, match, context, next_state):
        node = docutils.nodes.block_quote()
        mark_len = match.end()
        return context, next_state, self.enter(node, 'Section', indent=mark_len,
                                               indent_chars='>')

    def paragraph(self, match, context, next_state):
        node = docutils.nodes.paragraph()
        context.append(node)
        return context, next_state, self.enter(node, 'Paragraph')

    def blank(self, match, context, next_state):
        return context, next_state, []

    def ulist(self, match, context, next_state):
        """
        """
        node = docutils.nodes.bullet_list()
        node['bullet'] = match.group(1)
        context.append(node)
        return context, next_state, self.enter(node, 'UListContainer')

    def olist(self, match, context, next_state):
        node = docutils.nodes.enumerated_list()
        node['enumtype'] = 'arabic'
        node['start'] = int(match.group(1))
        node.delimiter = match.group(2)
        context.append(node)
        return context, next_state, self.enter(node, 'OListContainer')


@state
class Body(Section):
    def bof(self, context):
        context, result = MarkdownBaseState.bof(self, context)
        context.level = 0
        return context, result


@state
class Paragraph(MarkdownBaseState):
    initial_transitions = (
        'thematic_break',
        'section',
        'fence',
        'ulist',
        'olist_only_one',
        'blank',
        'paragraph',
    )

    def bof(self, context):
        context, result = MarkdownBaseState.bof(self, context)
        self.state_machine.lazy = True
        return context, result

    def paragraph(self, match, context, next_state):
        # TODO: handle inline markup
        context.append(docutils.nodes.Text(match.string))
        return context, next_state, []


@state
class Code(MarkdownBaseState):
    initial_transitions = (
        'fence',
        'blank',
        'paragraph',
    )

    def eof(self, context):
        joined = '\n'.join(context.children)
        context.clear()
        context.append(docutils.nodes.Text(joined))
        return []

    def fence(self, match, context, next_state):
        opening = match.group(1)
        if context.opening and context.opening in opening:
            self.state_machine.next_line()
            raise EOFError('End fence found')
        else:
            raise TransitionCorrection('paragraph')

    def paragraph(self, match, context, next_state):
        context.append(docutils.nodes.Text(match.string))
        return context, next_state, []
    blank = paragraph


@state
class UListContainer(MarkdownBaseState):
    initial_transitions = (
        'blank',
        'ulist',
    )

    def bof(self, context):
        context.tight = True
        return context, []

    def eof(self, context):
        if context.tight:
            # For tight lists, replace paragraphs with their contents directly
            for subnode in context.children[:]:
                if subnode.children:
                    child = subnode.children[0]
                    if isinstance(child, docutils.nodes.paragraph):
                        subnode.replace(child, child.children)
        return []

    def no_match(self, context, transitions):
        raise EOFError

    def blank(self, match, context, next_state):
        context.tight = False
        return context, next_state, []

    def list_item(self, match, context, next_state):
        node = docutils.nodes.list_item()
        context.append(node)
        mark_len = match.end()
        # FIXME: Negative indents will force new list
        self.state_machine.indent += match.start(1)
        return context, next_state, self.enter(node, 'ListItem', indent=mark_len)

    def ulist(self, match, context, next_state):
        if match.group(1) != context['bullet']:
            raise EOFError('New list')
        node = docutils.nodes.list_item()
        return self.list_item(match, context, next_state)


@state
class OListContainer(UListContainer):
    initial_transitions = (
        'blank',
        'olist',
    )

    def olist(self, match, context, next_state):
        if match.group(2) != context.delimiter:
            raise EOFError('New list')
        return self.list_item(match, context, next_state)


@state
class ListItem(Section):
    def blank(self, match, context, next_state):
        context.parent.tight = False
        return context, next_state, []
