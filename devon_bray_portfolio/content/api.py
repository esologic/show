"""
Interface through which other components of this application access the content of the portfolio.
TODO: There's a bit of redundancy, and a little more inheritance could be helpful.
"""

import string
import typing as t
from datetime import date
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple

from markdown import markdown
from PIL import Image, ImageSequence

from devon_bray_portfolio.content import schema

YAML_EXTENSION = "yaml"


class RenderedLocalMedia(NamedTuple):
    """
    Derived from the `LocalMedia` TD in `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    """

    label: str
    path: str


class RenderedLink(NamedTuple):
    """
    Derived from the `Link` TD in `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    """

    label: str
    link: str


class RenderedYouTubeVideo(NamedTuple):
    """
    Derived from the `YouTubeVideo` TD in `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    """

    label: str
    video_id: str


class RenderedEntry(NamedTuple):
    """
    Derived from the `SerializedEntry` TD in `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    By the time this is passed to flask, it assumes proper conditioning has been done on the
    text. Things like capitalization, standardization of cad vs. CAD etc should be completed by
    functions producing these objects. This is the "pretty" version of this information.
    """

    slug: str  # not present in `SerializedEntry`. This is set to the name of the source yaml file.
    title: str
    description: str
    explanation: str
    local_media: t.List[RenderedLocalMedia]
    youtube_videos: t.Optional[t.List[RenderedYouTubeVideo]]
    size: str
    domain: str
    primary_url: RenderedLink
    secondary_urls: t.Optional[t.List[RenderedLink]]
    press_urls: t.Optional[t.List[RenderedLink]]
    completion_date_verbose: str
    completion_year: str
    team_size: str
    involvement: str
    mediums: t.List[str]


class Section(NamedTuple):
    """
    Composed of a `SerializedSectionDescription` and then a list of `SerializedEntry` TDs from
    `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    Contains the entries that make up a whole section of the portfolio. Ex: Telapush, esologic
    Note: These could be written by hand but that would kind of complicate things.
    """

    title: str
    description: str
    primary_url: RenderedLink
    entries: t.List[RenderedEntry]


class Portfolio(NamedTuple):
    """
    Composed of `SerializedPortfolioDescription` and sub-sections as discovered on disk.
    """

    title: str
    description: str
    sections: t.List[Section]


def _render_link(url: schema.Link) -> RenderedLink:
    """
    Go from the serialized form to the rendered form.
    :param url: URL to convert.
    :return: Converted URL.
    """
    return RenderedLink(label=url["label"], link=str(url["link"]))  # just a plain string now


def _render_date(d: date, verbose: bool) -> str:
    """
    Canonical method to go from an entry's completion date to the way that's displayed in the
    portfolio.
    :param d: Date to convert.
    :return: String representation of the date.
    """
    return d.strftime("%B of %Y") if verbose else d.strftime("%Y")


def _render_mediums(mediums: t.List[schema.Medium]) -> t.List[str]:
    """
    Makes sure capitalization, and format etc are uniform.
    Implementation is a bit ugly, this could probably be done with a single regex if needed.
    :param mediums: To render.
    :return: Rendered strings for display.
    """

    def convert(medium: str) -> str:
        for bad, good in [("3d", "3D"), ("Cad", "CAD"), ("Led", "LED"), ("Pcb", "PCB")]:
            if bad in medium:
                return medium.replace(bad, good)

        return medium

    return sorted([convert(medium) for medium in [string.capwords(medium) for medium in mediums]])


def _render_link_list(
    link_list: t.Optional[t.List[schema.Link]],
) -> t.Optional[t.List[RenderedLink]]:
    """
    Helper function, renders a list of links.
    :param link_list: Links to render.
    :return: Rendered links.
    """
    return [_render_link(url) for url in link_list] if link_list else None


def _render_local_media(
    media_directory: Path, yaml_path: Path, local_media: schema.LocalMedia
) -> RenderedLocalMedia:
    """
    Copies, processes images from their origins in the entry folders to their destinations
    in the `media_directory` folder. Returns a new NT, with a reference to their path
    relative to `media_directory`.
    :param local_media: Reference to the file in the entry directory.
    :return: Fields converted to strings, paths relative to `media_directory`.
    """

    max_size = (3000, 3000)
    name = local_media["path"].name
    output_path = media_directory.joinpath(name)

    if not output_path.exists():

        image = Image.open(str(yaml_path.parent.joinpath(local_media["path"])))

        if getattr(image, "is_animated", False):

            frames = ImageSequence.Iterator(image)

            # Wrap on-the-fly thumbnail generator
            def thumbnails(f: ImageSequence.Iterator) -> t.Iterator[Image.Image]:
                for frame in f:
                    thumbnail = frame.copy()
                    thumbnail.thumbnail(max_size, Image.ANTIALIAS)
                    yield thumbnail

            frames = thumbnails(frames)

            # Save output
            om = next(frames)  # Handle first frame separately
            om.info = image.info  # Copy sequence info
            om.save(str(output_path), save_all=True, append_images=list(frames), loop=0)

        else:
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            image.thumbnail(max_size)

            image.save(str(output_path))

    return RenderedLocalMedia(label=markdown(local_media["label"]), path=str(name))


def _read_entry(yaml_path: Path, media_directory: Path) -> RenderedEntry:
    """
    Read in a portfolio entry from it's yaml path on disk, normalize formatting and render the
    different fields then return the resulting NT.
    :param yaml_path: Path to the entry's yaml file.
    :param media_directory: Flask's `static` directory (or a subdir of the static dir).
    Images are copied from their original location in the entry directories to this folder.
    Some processing is done on these images to assure that they're not massive.
    :return: The `RenderedEntry`, ready for consumption by jinja via flask.
    All fields (members?) in this output should be strings.
    """

    serialized_entry = schema.read_portfolio_element(yaml_path, schema.SerializedEntry)

    with Pool() as p:
        local_media = p.map(
            partial(_render_local_media, media_directory, yaml_path), serialized_entry.local_media
        )

    return RenderedEntry(
        slug=yaml_path.with_suffix("").name,
        title=serialized_entry.title,
        description=serialized_entry.description,
        explanation=markdown(serialized_entry.explanation),
        local_media=local_media,
        youtube_videos=[
            RenderedYouTubeVideo(label=markdown(video["label"]), video_id=video["video_id"])
            for video in serialized_entry.youtube_videos
        ]
        if serialized_entry.youtube_videos
        else None,
        size=serialized_entry.size.value,
        domain=string.capwords(serialized_entry.domain.value),
        primary_url=_render_link(serialized_entry.primary_url),
        secondary_urls=_render_link_list(serialized_entry.secondary_urls),
        press_urls=_render_link_list(serialized_entry.press_urls),
        completion_date_verbose=_render_date(serialized_entry.completion_date, verbose=True),
        completion_year=_render_date(serialized_entry.completion_date, verbose=False),
        team_size=string.capwords(serialized_entry.team_size.value),
        involvement=serialized_entry.involvement,
        mediums=_render_mediums(serialized_entry.mediums),
    )


def _find_yaml(directory: Path) -> Path:
    """
    Search a given directory for a yaml file.
    Note: all callers only want to find a single yaml file in the given directory, so if more
    than one yaml file is found, an error is raised.
    :param directory: Directory to search.
    :return: Path to the yaml file.
    :raises ValueError: If more than one yaml is found in the given directory, or if no yaml is
    found
    """

    yaml_paths = list(directory.glob(f"*.{YAML_EXTENSION}"))

    if len(yaml_paths) > 1:
        raise ValueError(f"Found too many yaml files in dir: {directory}")

    try:
        output = next(iter(yaml_paths))
    except StopIteration as e:
        raise ValueError(f"Couldn't find a yaml in directory: {directory}") from e

    return output


def _directories_in_directory(directory: Path) -> t.Iterator[Path]:
    """
    For the given directory, yield paths to directories within that directory.
    :param directory: Path to search
    :return: Sub directories, is not recursive.
    """

    yield from [path for path in directory.iterdir() if path.is_dir()]


def _read_section(section_directory: Path, static_content_directory: Path) -> Section:
    """
    Given a `section_directory` (so a directory with a top-level yaml, and a bunch of directories
    that each describe a portfolio entry), load the contents as a Section, modifying the contents
    such that it'll be fit for rendering.
    :param section_directory: Directory that corresponds with the section.
    :param static_content_directory: Images from entries are copied/compressed to this directory.
    :return: In-memory version of Section.
    """

    section_description_path = _find_yaml(section_directory)
    section_description = schema.read_portfolio_element(
        section_description_path, schema.SerializedSectionDescription
    )

    return Section(
        description=section_description.description,
        title=section_description.title,
        primary_url=_render_link(section_description.primary_url),
        entries=[
            _read_entry(_find_yaml(path), static_content_directory)
            for path in _directories_in_directory(section_directory)
        ],
    )


def discover_portfolio(sections_directory: Path, static_content_directory: Path) -> Portfolio:
    """
    Loads the portfolio as it's represented on disk (as a collection of directories and images and
    yaml files) into memory so it can be displayed by other components of this application (flask)
    :param sections_directory: Contains section directories, and a top level yaml describing the
    portfolio.
    :param static_content_directory: Media discovered is copied to this directory so it can
    be served by flask.
    :return: In-memory version of the portfolio.
    """

    portfolio_description_path = _find_yaml(sections_directory)
    portfolio_description = schema.read_portfolio_element(
        portfolio_description_path, schema.SerializedPortfolioDescription
    )

    output = Portfolio(
        title=portfolio_description.title,
        description=portfolio_description.description,
        sections=[
            _read_section(section_directory, static_content_directory)
            for section_directory in _directories_in_directory(sections_directory)
        ],
    )
    return output
