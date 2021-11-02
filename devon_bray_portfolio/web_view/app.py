"""
Flask entry point
"""

import itertools
import os
import typing as t
from pathlib import Path

from flask import Flask, render_template

from devon_bray_portfolio.content.api import discover_portfolio

_CURRENT_DIRECTORY = Path(os.path.dirname(os.path.abspath(__file__)))


def create_app() -> Flask:
    """

    :return:
    """

    app = Flask(__name__)

    current_portfolio = discover_portfolio(
        sections_directory=Path(
            "/home/devon/Documents/projects/devon_bray_portfolio"
            "/devon_bray_portfolio/content/portfolio"
        ),
        static_content_directory=_CURRENT_DIRECTORY.joinpath("static"),
    )

    lookup = {
        entry.slug: entry
        for entry in itertools.chain.from_iterable(
            [section.entries for section in current_portfolio.sections]
        )
    }

    @app.route("/")
    def render_portfolio() -> str:  # pylint: disable=unused-variable
        """

        :return:
        """
        return render_template(
            "portfolio.html",
            portfolio=current_portfolio,
        )

    @app.route("/<string:slug>")
    def render_slug(slug: str) -> str:  # pylint: disable=unused-variable
        """

        :return:
        """
        return render_template(
            "entry.html",
            entry=lookup[slug],
        )

    @app.errorhandler(Exception)  # type: ignore[arg-type]
    @app.errorhandler(404)
    def page_not_found(  # pylint: disable=unused-variable
        e: t.Union[t.Type[KeyError], int]
    ) -> t.Tuple[str, int]:
        """
        TODO: Maybe I want to do a cheeky email thing here?
        :param e:
        :return:
        """
        return f"No page! Exception: {e}", 404

    return app


if __name__ == "__main__":

    create_app().run(host="0.0.0.0")
