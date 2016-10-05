
import os

import docutils.parsers.markdown
import pytest


@pytest.mark.parametrize('case', [
    os.path.splitext(filename)[0] for filename in
    os.listdir(os.path.join(os.path.dirname(__file__), 'cases'))
    if filename.endswith('.md')
])
def test_format_remaining(case):
    document = docutils.utils.new_document(case)
    with open(os.path.join(os.path.dirname(__file__), 'cases', case+'.md')) as handle:
        contents = handle.read()
    parser = docutils.parsers.markdown.MarkdownParser()
    parser.parse(contents, document)
    print(document)
