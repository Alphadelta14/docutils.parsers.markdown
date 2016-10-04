
import docutils.parsers
import docutils.statemachine


class MarkdownParser(docutils.parsers.Parser):
    supported = ('markdown', 'md')

    def parse(self, inputstring, document):
        raise NotImplementedError()
