"""
Flask entry point
"""

import itertools
import os
import typing as t
from pathlib import Path

from flask import Flask, render_template

from devon_bray_portfolio.content_api import ImagesConfig, discover_portfolio
from devon_bray_portfolio.paths_common import CONTENT_ROOT

_CURRENT_DIRECTORY = Path(os.path.dirname(os.path.abspath(__file__)))


def create_app(portfolio_content_root: Path = CONTENT_ROOT, write_images: bool = False) -> Flask:
    """
    Creates the flask object to serve the portfolio, or to be rendered statically.
    :param portfolio_content_root: Root path of content to be rendered into a portfolio.
    :param write_images: When images are loaded from content directories, they are modified.
    Set this to True if you want them to be re-modified if they don't already exist.
    :return: Flask object for serving or rendering.
    """

    app = Flask(__name__)

    current_portfolio = discover_portfolio(
        sections_directory=portfolio_content_root,
        static_content_directory=_CURRENT_DIRECTORY.joinpath("static"),
        image_config=ImagesConfig(
            large_image_max_dimensions=(2000, 2000),
            small_image_max_dimensions=(500, 500),
            icon_max_dimensions=(50, 50),
            quality=95,
            force_rewrite=write_images,
        ),
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
        Top level view of portfolio. Shows all the entries grouped by section.
        :return: HTML.
        """
        return render_template(
            "portfolio.html",
            portfolio=current_portfolio,
        )

    @app.route("/<string:slug>/")
    def render_slug(slug: str) -> str:  # pylint: disable=unused-variable
        """
        Renders an individual portfolio entry.
        :return: HTML
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
        404 Error Page.
        TODO: Maybe I want to do a cheeky email thing here?
        :param e: Error that was raised
        :return: HTML
        """
        return f"No page! Exception: {e}", 404

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0")
