"""
Flask entry point
"""

import os
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

    @app.route("/")
    def portfolio() -> str:  # pylint: disable=unused-variable
        """

        :return:
        """
        return render_template(
            "portfolio.html",
            portfolio=current_portfolio,
        )

    return app


if __name__ == "__main__":

    create_app().run()
