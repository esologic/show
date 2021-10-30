"""
Flask entry point
"""

from pathlib import Path

from flask import Flask, render_template

from devon_bray_portfolio.content.api import discover_portfolio


def create_app() -> Flask:
    """

    :return:
    """

    app = Flask(__name__)

    sections = discover_portfolio(
        sections_directory=Path(
            "/home/devon/Documents/projects/devon_bray_portfolio"
            "/devon_bray_portfolio/content/sections"
        ),
        static_content_directory=Path("./static"),
    )

    @app.route("/")
    def portfolio() -> str:  # pylint: disable=unused-variable
        """

        :return:
        """
        return render_template(
            "entries.html",
            sections=sections,
        )

    return app


if __name__ == "__main__":

    create_app().run()
