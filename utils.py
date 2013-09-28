"""
Some utils function here
"""
import markdown

def convert_markdown_text(md_text):
    return markdown.markdown(md_text, extensions=['extra', 'codehilite(linenums=False,css_class=prettyprint)'])

