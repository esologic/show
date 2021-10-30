"""
Flask entry point
"""

from pathlib import Path

from flask import Flask, render_template

from devon_bray_portfolio.content.api import discover_sections

app = Flask(__name__)


@app.route("/")
def portfolio() -> str:
    """

    :return:
    """
    return render_template(
        "entries.html",
        sections=discover_sections(
            Path(
                "/home/devon/Documents/projects/devon_bray_portfolio"
                "/devon_bray_portfolio/content/sections"
            )
        ),
    )


if __name__ == "__main__":

    app.run()
