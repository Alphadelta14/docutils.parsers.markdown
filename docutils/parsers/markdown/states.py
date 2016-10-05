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


class MarkdownStateMachine(StateMachine):
    """Markdown master StateMachine
    """
    @classmethod
    def create(cls):
        inst = cls(initial_state='Body', state_classes=state_classes)
        return inst

    def run(self, input_lines, input_offset=0, context=None,
            input_source=None, initial_state=None):
        return StateMachine.run(self, input_lines, input_offset, context,
                                  input_source, initial_state)


class MarkdownBaseState(State):
    node_class = docutils.nodes.paragraph
    nested_sm_kwargs = {
        'state_classes': state_classes,
        'initial_state': 'Body',
    }

    def xbof(self, context):
        if self.node_class is not None:
            node = self.node_class()
            context.append(node)
            context = node
        return context, []

    def enter(self, context, next_state):
        substate_machine = self.nested_sm(**self.nested_sm_kwargs)
        results = substate_machine.run(
            self.state_machine.input_lines[self.state_machine.line_offset+1:],
            self.state_machine.abs_line_offset(),
            context=context, initial_state=next_state
        )
        self.state_machine.goto_line(substate_machine.abs_line_offset())
        return results


@state
class Section(MarkdownBaseState):
    node_class = docutils.nodes.section
    patterns = {
        'section': r'(#+)([^#].+)',
        'paragraph': r'.',
        'new_paragraph': r'',
    }
    initial_transitions = (
        'section',
        'paragraph',
        'new_paragraph',
    )

    def section(self, match, context, next_state):
        level = match.group(1).count('#')
        if level <= context.level:
            raise EOFError()
        subcontext = docutils.nodes.section()
        subcontext.level = level
        context.append(subcontext)
        header = docutils.nodes.title(text=match.group(2).lstrip())
        subcontext.append(header)
        return context, None, self.enter(subcontext, 'Section')

    def new_paragraph(self, match, context, next_state):
        node = docutils.nodes.paragraph()
        context.append(node)
        return context, next_state, []

    def paragraph(self, match, context, next_state):
        """Append text to the last paragraph.

        If the last child was not a paragraph, step back and create a new one.
        `self.previous_line()` is called manually because `self.new_paragraph`
        will swallow a line, so we'd like it to swallow the line before the
        paragraph start. (An implicit call to `self.previous_line()` is made
        when correcting transition)
        """
        if not context.children:
            self.state_machine.previous_line()
            raise TransitionCorrection('new_paragraph')
        last_child = context.children[-1]
        if not isinstance(last_child, docutils.nodes.paragraph):
            self.state_machine.previous_line()
            raise TransitionCorrection('new_paragraph')
        last_child.append(docutils.nodes.Text(match.string+'\n'))
        return context, next_state, []


@state
class Body(Section):
    def bof(self, context):
        context, result = MarkdownBaseState.bof(self, context)
        context.level = 0
        return context, result


@state
class Text(MarkdownBaseState):
    node_class = None
    patterns = {
        'header': r'(#+)([^#].+)',
        # 'line': r'([!-/:-@[-`{-~])\1* *$',
        'text': r''
    }
    initial_transitions = (
        'header',
        # 'line',
        'text',
    )

    def header(self, match, context, next_state):
        print(match, context, next_state)
        return context, None, []

    def text(self, match, context, next_state):
        """Falls back to default state."""
        return context, None, []
