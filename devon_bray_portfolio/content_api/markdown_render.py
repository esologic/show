"""
Functionality related to loading markdown strings to html.
"""

from markdown import markdown


def render_markdown(text: str) -> str:
    """
    Converts a string formatted with markdown to html.
    Warning! When passing this into jinja, you need to mark it with `safe`.
    Ex:
        {{ portfolio.description | safe }}
    TODO: Would like to communicate with YAML which fields are markdown enabled or not.
    :param text: Text with markdown characters.
    :return: HTML
    """

    return markdown(text, extensions=["markdown3_newtab"])
