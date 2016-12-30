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


def indented_lines(lines, indent=0, permitted=' '):
    """Trims indentation from lines.

    Returns:

    - `lines`: a new trimmed list(str) of lines
    """

    def trimmed():
        for line in lines:
            if line.strip('\t '):
                # commonmark: @blank-line
                yield ''
                continue
            if not indent:
                yield line
                continue
            # only expand tabs at the start of the line
            while '\t' in line[:indent]:
                line = line[:indent].expandtabs(4)+line[indent:]
            if line[:indent].strip(permitted):
                return
    return [line for line in trimmed()]


class MarkdownStateMachine(StateMachine):
    """Markdown master StateMachine
    """
    def __init__(self, state_classes, initial_state, debug=False):
        StateMachine.__init__(self, state_classes, initial_state, debug)

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
        'fence': r'\s{0,3}(```|~~~)',
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

    def slice_lines(self, nth=0):
        ofs = self.state_machine.line_offset+nth
        self.state_machine.next_line(nth)
        return self.state_machine.input_lines[ofs:]

    def enter(self, context, next_state, input_lines=None):
        """Enters a nested statemachine.

        Parameters:

        - `context`: `docutils.nodes.Node`
        - `next_state` : str
        """
        substate_machine = self.nested_sm(**self.nested_sm_kwargs)
        input_offset = self.state_machine.abs_line_offset()
        if input_lines is None:
            input_lines = self.slice_lines()
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
        'fence',
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
        if level <= context.level:
            raise EOFError()
        trans_context = context
        while level > context.level:
            subcontext = docutils.nodes.section()
            subcontext.level = level
            trans_context.append(subcontext)
            level -= 1
            trans_context = subcontext
        header = docutils.nodes.title(text=match.group(2).lstrip())
        subcontext.append(header)
        lines = self.slice_lines(1)
        return context, next_state, self.enter(subcontext, 'Section', lines)

    def paragraph(self, match, context, next_state):
        """Append text to the last paragraph.

        If the last child was not a paragraph, step back and create a new one.
        `self.previous_line()` is called manually because `self.new_paragraph`
        will swallow a line, so we'd like it to swallow the line before the
        paragraph start. (An implicit call to `self.previous_line()` is made
        when correcting transition)
        """
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

    def paragraph(self, match, context, next_state):
        # TODO: handle inline markup
        context.append(docutils.nodes.Text(match.string))
        return context, next_state, []


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

    def slice_lines(self, nth=0):
        lines = MarkdownBaseState.slice_lines(nth)
        return lines

    def ulist(self, match, context, next_state):
        if match.group(1) != context['bullet']:
            raise EOFError('New list')
        node = docutils.nodes.list_item()
        return context, next_state, self.enter(node, 'ListItem')


@state
class OListContainer(UListContainer):
    initial_transitions = (
        'blank',
        'olist',
    )

    def olist(self, match, context, next_state):
        if match.group(2) != context.delimiter:
            raise EOFError('New list')
        node = docutils.nodes.list_item()
        return context, next_state, self.enter(node, 'ListItem')


@state
class ListItem(Section):
    def blank(self, match, context, next_state):
        context.parent.tight = False
        return context, next_state, []

