"""Markdown StateMachine and States

>>> state_machine = MarkdownStateMachine.create()
"""

import docutils.nodes
from docutils.statemachine import StateMachineWS, StateWS

__all__ = ['MarkdownStateMachine']

state_classes = []


def state(cls):
    """Wraps classes to track that they are states.
    """
    state_classes.append(cls)
    return cls


class MarkdownStateMachine(StateMachineWS):
    """Markdown master StateMachine
    """
    @classmethod
    def create(cls):
        inst = cls(initial_state='Body', state_classes=state_classes)
        return inst

    def run(self, input_lines, input_offset=0, context=None,
            input_source=None, initial_state=None):
        return StateMachineWS.run(self, input_lines, input_offset, context,
                                  input_source, initial_state)


class MarkdownBaseState(StateWS):
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
        return substate_machine.run(
            self.state_machine.input_lines[self.state_machine.line_offset+1:],
            self.state_machine.abs_line_offset(),
            context=context, initial_state=next_state
        )


@state
class Section(MarkdownBaseState):
    node_class = docutils.nodes.section
    patterns = {
        'section': r'(#+) *([^# ].+)',
    }
    initial_transitions = (
        'section',
    )

    def xbof(self, context):
        context, result = MarkdownBaseState.bof(self, context)
        context.level = 0
        return context, result

    def section(self, match, context, next_state):
        subcontext = docutils.nodes.section()
        context.append(subcontext)
        header = docutils.nodes.header()
        header.append(docutils.nodes.Text(match.group(2)))
        subcontext.append(header)
        return context, None, self.enter(subcontext, 'Section')

    def text(self, match, context, next_state):
        """Falls back to default state."""
        context.document.append(docutils.nodes.Text(match.string))
        return context, 'Text', []


@state
class Body(Section):
    pass


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
