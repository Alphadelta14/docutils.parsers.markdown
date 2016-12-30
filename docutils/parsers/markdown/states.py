"""Markdown StateMachine and States

>>> state_machine = MarkdownStateMachine.create()
"""

import docutils.nodes
from docutils.statemachine import StateMachine, State, TransitionCorrection

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
        'ulist': r'([*+-]) ',
        'olist': r'(\d+)([.)]) ',
        'section': r'\s{0,3}(#{1,6})([^#].*)',
        'fence': r'\s{0,3}(```|~~~)',
        'thematic_break': r'\s{0,3}([*_-])\s*(\1\s*){2,}$',
        'paragraph': r'.',
        'paragraph_end': r'[\t ]*$',
    }

    def enter(self, context, next_state, nth=0, indent=0):
        """Enters a nested statemachine.

        Parameters:

        - `context`: `docutils.nodes.Node`
        - `next_state` : str
        """
        substate_machine = self.nested_sm(**self.nested_sm_kwargs)
        ofs = self.state_machine.line_offset+nth
        results = substate_machine.run(
            indented_lines(self.state_machine.input_lines[ofs:], indent),
            self.state_machine.abs_line_offset(),
            context=context, initial_state=next_state
        )
        self.state_machine.goto_line(substate_machine.abs_line_offset())
        return results


@state
class Section(MarkdownBaseState):
    initial_transitions = (
        'thematic_break',
        'section',
        'ulist',
        'paragraph',
        'new_paragraph',
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
        return context, next_state, self.enter(subcontext, 'Section', nth=1)

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

    def ulist(self, match, context, next_state):
        """
        """
        node = docutils.nodes.bullet_list()
        node['bullet'] = match.group(1)
        context.append(node)
        return context, next_state, self.enter(node, 'ListContainer')

    def olist(self, match, context, next_state):
        node = docutils.nodes.enumerated_list()
        node['enumtype'] = 'arabic'
        context.append(node)
        return context, next_state, self.enter(node, 'ListContainer')


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
        'paragraph_end',
        'paragraph',
    )

    def paragraph_end(self, match, context, next_state):
        raise EOFError('End of paragraph')
    thematic_break = paragraph_end
    section = paragraph_end
    fence = paragraph_end

    def paragraph(self, match, context, next_state):
        # TODO: handle inline markup
        context.append(docutils.nodes.Text(match.string))
        return context, next_state, []
