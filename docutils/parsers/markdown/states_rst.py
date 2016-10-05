"""Markdown StateMachine and States

>>> state_machine = MarkdownStateMachine.create()
"""

import docutils.nodes
from docutils.parsers import rst
from docutils.statemachine import StateMachineWS, StateWS

__all__ = ['MarkdownStateMachine']

state_classes = []


def register_state(cls):
    """Wraps classes to track that they are states.
    """
    state_classes.append(cls)
    return cls


class MarkdownStateMachine(rst.states.RSTStateMachine):
    """Markdown master StateMachine
    """
    @classmethod
    def create(cls):
        inst = cls(initial_state='Body', state_classes=(Body, Text))
        return inst


class MarkdownStateOverrideMixin(StateWS):
    def __init__(self, state_machine, debug=False):
        self.nested_sm_kwargs = {'state_classes': state_classes,
                                 'initial_state': 'Body'}
        StateWS.__init__(self, state_machine, debug)


class Inliner(rst.states.Inliner):
    def init_customizations(self, settings):
        pass


@register_state
class Body(MarkdownStateOverrideMixin, rst.states.Body):
    patterns = rst.states.Body.patterns.copy()
    patterns.pop('explicit_markup')
    patterns['heading'] = r'(#+) *([^# ].+)'
    initial_transitions = list(rst.states.Body.initial_transitions)
    initial_transitions.remove('explicit_markup')
    initial_transitions.insert(0, 'heading')

    def heading(self, match, context, next_state):
        lineno = self.state_machine.abs_line_number()
        title = match.group(2)
        source = match.string
        style = '#'
        # context[:] = []
        self.section(title, source, style, lineno - 1, [])
        return [], next_state, []


@register_state
class Text(MarkdownStateOverrideMixin, rst.states.Text):
    pass
