# docutils.parsers.markdown
This adds support for Markdown files to be processed as part of docutils.

## Installation

```
pip install docutils.parsers.markdown
```

Or for development, after cloning this repo:

```
pip install -r requirements.txt
```

## Sphinx

To use with Sphinx, add or modify the following options in your `conf.py`.

```python

extensions = ['docutils.parsers.markdown']

source_suffix = ['.rst', 'md']

```
