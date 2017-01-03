
import docutils.parsers
import docutils.statemachine

from docutils.parsers.markdown import states
from docutils.parsers.markdown.context import Context


class Parser(docutils.parsers.Parser):
    supported = ('markdown', 'md')

    def parse(self, inputstring, document):
        self.setup_parse(inputstring, document)
        self.statemachine = states.MarkdownStateMachine.create()
        try:
            inputstring = unicode(inputstring.decode('utf-8'))
        except UnicodeDecodeError:
            pass
        inputlines = docutils.statemachine.string2lines(
            inputstring,
            convert_whitespace=True
        )
        # inliner = states.Inliner()
        context = Context(document)
        self.statemachine.run(inputlines, context=document)
        self.finish_parse()
