"""Main module."""

from flask_frozen import Freezer

from devon_bray_portfolio.web_view.app import create_app


def main() -> None:
    """
    This function creates a number of static HTML files that can be served on their own as the
    portfolio.
    :return: None
    """

    app = create_app(write_images=True)

    # This lets you just copy and paste the resulting directory anywhere and assets are located
    # correctly.
    app.config["FREEZER_RELATIVE_URLS"] = True

    freezer = Freezer(app)
    freezer.freeze()


if __name__ == "__main__":
    main()
