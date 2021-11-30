"""
Interface through which other components of this application access the content of the portfolio.
TODO: There's a bit of redundancy, and a little more inheritance could be helpful.
"""
import itertools
import shutil
import typing as t
from datetime import date
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple

from devon_bray_portfolio.content_api import schema
from devon_bray_portfolio.content_api.images import (
    ImagesConfig,
    ImageSizes,
    RenderedLocalMedia,
    render_local_media,
    unpack_image_sizes,
)
from devon_bray_portfolio.content_api.markdown_render import render_markdown

YAML_EXTENSION = "yaml"


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


class RenderedEntryWithoutNeighbors(NamedTuple):
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
    featured_media: RenderedLocalMedia
    local_media: t.Optional[t.Tuple[RenderedLocalMedia, ...]]
    youtube_videos: t.Optional[t.Tuple[RenderedYouTubeVideo, ...]]
    size: str
    domain: str
    primary_url: RenderedLink
    secondary_urls: t.Optional[t.Tuple[RenderedLink, ...]]
    press_urls: t.Optional[t.Tuple[RenderedLink, ...]]
    completion_date: date
    completion_date_verbose: str
    completion_year: str
    team_size: str
    involvement: str
    mediums: t.Tuple[str, ...]
    primary_color: str
    favicon_path: str
    top_image: RenderedLocalMedia
    visible: bool


class RenderedEntry(NamedTuple):
    """
    Adds the next and previous items.
    """

    slug: str  # not present in `SerializedEntry`. This is set to the name of the source yaml file.
    title: str
    description: str
    explanation: str
    featured_media: RenderedLocalMedia
    local_media: t.Optional[t.Tuple[RenderedLocalMedia, ...]]
    youtube_videos: t.Optional[t.Tuple[RenderedYouTubeVideo, ...]]
    size: str
    domain: str
    primary_url: RenderedLink
    secondary_urls: t.Optional[t.Tuple[RenderedLink, ...]]
    press_urls: t.Optional[t.Tuple[RenderedLink, ...]]
    completion_date: date
    completion_date_verbose: str
    completion_year: str
    team_size: str
    involvement: str
    mediums: t.Tuple[str, ...]
    primary_color: str
    favicon_path: str
    top_image: RenderedLocalMedia
    visible: bool

    # Filled when the section is rendered
    previous_entry: t.Optional["RenderedEntryWithoutNeighbors"] = None
    next_entry: t.Optional["RenderedEntryWithoutNeighbors"] = None


class SectionIncompleteEntries(NamedTuple):
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
    entries: t.List[RenderedEntryWithoutNeighbors]
    primary_color: str
    logo: RenderedLocalMedia
    rank: int


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
    entries: t.List[RenderedEntry]
    primary_color: str
    logo: RenderedLocalMedia
    rank: int


class Portfolio(NamedTuple):
    """
    Composed of `SerializedPortfolioDescription` and sub-sections as discovered on disk.
    """

    title: str
    description: str
    explanation: str
    conclusion: str
    sections: t.List[Section]
    contact_urls: t.Tuple[RenderedLink, ...]
    email: str
    header_top_image: RenderedLocalMedia
    header_bottom_image: RenderedLocalMedia
    icon: RenderedLocalMedia
    resume_path: t.Optional[str]
    portrait: RenderedLocalMedia
    header_background: RenderedLocalMedia


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


def _capitalize_string(text: str) -> str:
    """
    Canonical function to capitalize a string.
    :param text: To capitalize.
    :return: Capitalized.
    """
    return str.title(text)


def _render_mediums(mediums: t.List[schema.Medium]) -> t.Tuple[str, ...]:
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

    return tuple(
        sorted([convert(medium) for medium in [_capitalize_string(medium) for medium in mediums]])
    )


def _render_link_list(
    link_list: t.Optional[t.List[schema.Link]],
) -> t.Optional[t.Tuple[RenderedLink, ...]]:
    """
    Helper function, renders a list of links.
    :param link_list: Links to render.
    :return: Rendered links.
    """
    return tuple(_render_link(url) for url in link_list) if link_list else None


def _read_entry_from_disk(
    yaml_path: Path,
    media_directory: Path,
    primary_color: str,
    return_button_image: RenderedLocalMedia,
    image_sizes: ImageSizes,
) -> RenderedEntryWithoutNeighbors:
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

    media_processor = partial(
        render_local_media, media_directory, yaml_path, None, image_sizes.large
    )

    if serialized_entry.local_media is not None:
        with Pool(processes=5) as p:
            local_media = tuple(
                p.map(
                    media_processor,
                    serialized_entry.local_media,
                )
            )
    else:
        local_media = None

    slug = yaml_path.with_suffix("").name

    youtube_videos = (
        tuple(
            RenderedYouTubeVideo(label=render_markdown(video["label"]), video_id=video["video_id"])
            for video in serialized_entry.youtube_videos
        )
        if serialized_entry.youtube_videos is not None
        else None
    )

    return RenderedEntryWithoutNeighbors(
        slug=slug,
        title=serialized_entry.title,
        description=serialized_entry.description,
        explanation=render_markdown(serialized_entry.explanation),
        featured_media=media_processor(serialized_entry.featured_media),
        local_media=local_media,
        youtube_videos=youtube_videos,
        size=serialized_entry.size.value,
        domain=_capitalize_string(serialized_entry.domain.value),
        primary_url=_render_link(serialized_entry.primary_url),
        secondary_urls=_render_link_list(serialized_entry.secondary_urls),
        press_urls=_render_link_list(serialized_entry.press_urls),
        completion_date=serialized_entry.completion_date,
        completion_date_verbose=_render_date(serialized_entry.completion_date, verbose=True),
        completion_year=_render_date(serialized_entry.completion_date, verbose=False),
        team_size=_capitalize_string(serialized_entry.team_size.value),
        involvement=serialized_entry.involvement,
        mediums=_render_mediums(serialized_entry.mediums),
        primary_color=primary_color,
        favicon_path=render_local_media(
            media_directory=media_directory,
            yaml_path=yaml_path,
            new_file_name=f"{slug}_icon.png",
            image_config=image_sizes.icon,
            local_media=serialized_entry.featured_media,
        ).path,
        top_image=return_button_image,
        visible=serialized_entry.visible,
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


def _read_section_from_disk(
    section_directory: Path,
    static_content_directory: Path,
    return_button_image: RenderedLocalMedia,
    image_sizes: ImageSizes,
) -> SectionIncompleteEntries:
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

    primary_color = str(section_description.primary_color)

    entries = list(
        sorted(
            [
                _read_entry_from_disk(
                    yaml_path=_find_yaml(path),
                    media_directory=static_content_directory,
                    primary_color=primary_color,
                    return_button_image=return_button_image,
                    image_sizes=image_sizes,
                )
                for path in _directories_in_directory(section_directory)
            ],
            key=lambda entry: entry.completion_date,
            reverse=True,
        )
    )

    return SectionIncompleteEntries(
        description=render_markdown(section_description.description),
        title=section_description.title,
        entries=entries,
        primary_color=primary_color,
        logo=render_local_media(
            media_directory=static_content_directory,
            yaml_path=section_description_path,
            new_file_name=None,
            image_config=image_sizes.small,
            local_media=section_description.logo,
        ),
        rank=section_description.rank,
    )


def _fill_entry_neighbors(
    entry: RenderedEntryWithoutNeighbors,
    previous_next: t.Tuple[
        t.Optional[RenderedEntryWithoutNeighbors], t.Optional[RenderedEntryWithoutNeighbors]
    ],
) -> RenderedEntry:
    """
    Promotes `RenderedEntry` it's two neighbors.
    :param entry: Entry to modify.
    :param previous_next: Neighbors.
    :return: new NT.
    """
    previous_entry, next_entry = previous_next

    return RenderedEntry(
        slug=entry.slug,
        title=entry.title,
        description=entry.description,
        explanation=entry.explanation,
        featured_media=entry.featured_media,
        local_media=entry.local_media,
        youtube_videos=entry.youtube_videos,
        size=entry.size,
        domain=entry.domain,
        primary_url=entry.primary_url,
        secondary_urls=entry.secondary_urls,
        press_urls=entry.press_urls,
        completion_date=entry.completion_date,
        completion_date_verbose=entry.completion_date_verbose,
        completion_year=entry.completion_year,
        team_size=entry.team_size,
        involvement=entry.involvement,
        mediums=entry.mediums,
        primary_color=entry.primary_color,
        favicon_path=entry.favicon_path,
        top_image=entry.top_image,
        previous_entry=previous_entry,
        next_entry=next_entry,
        visible=entry.visible,
    )


def discover_portfolio(
    sections_directory: Path, static_content_directory: Path, image_config: ImagesConfig
) -> Portfolio:
    """
    Loads the portfolio as it's represented on disk (as a collection of directories and images and
    yaml files) into memory so it can be displayed by other components of this application (flask)
    :param sections_directory: Contains section directories, and a top level yaml describing the
    portfolio.
    :param static_content_directory: Media discovered is copied to this directory so it can
    be served by flask.
    :param image_config: Settings for modifying images for inclusion in the portfolio.
    :return: In-memory version of the portfolio.
    """

    portfolio_description_path = _find_yaml(sections_directory)
    portfolio_description = schema.read_portfolio_element(
        portfolio_description_path, schema.SerializedPortfolioDescription
    )

    images_sizes = unpack_image_sizes(image_config)

    return_button_image = render_local_media(
        media_directory=static_content_directory,
        yaml_path=portfolio_description_path,
        new_file_name=None,
        image_config=images_sizes.small,
        local_media=portfolio_description.return_image,
    )

    sections = sorted(
        [
            _read_section_from_disk(
                section_directory=section_directory,
                static_content_directory=static_content_directory,
                return_button_image=return_button_image,
                image_sizes=images_sizes,
            )
            for section_directory in _directories_in_directory(sections_directory)
        ],
        key=lambda section: section.rank,
    )

    entries: t.List[RenderedEntryWithoutNeighbors] = list(
        itertools.chain.from_iterable([section.entries for section in sections])
    )

    def at_index(i: int) -> t.Optional[RenderedEntryWithoutNeighbors]:
        """
        Biz logic for getting neighbors.
        :param i: Index
        :return: The entry or None if there shouldn't be an entry.
        """
        if i < 0:
            return None
        try:
            return entries[i]
        except IndexError:
            return None

    lookup: t.Dict[
        RenderedEntryWithoutNeighbors,
        t.Tuple[
            t.Optional[RenderedEntryWithoutNeighbors], t.Optional[RenderedEntryWithoutNeighbors]
        ],
    ] = {entry: (at_index(index - 1), at_index(index + 1)) for index, entry in enumerate(entries)}

    sections_with_entry_neighbors = [
        Section(
            title=section.title,
            description=section.description,
            entries=[
                _fill_entry_neighbors(entry, lookup[entry])
                for entry in section.entries
                if entry.visible
            ],
            primary_color=section.primary_color,
            logo=section.logo,
            rank=section.rank,
        )
        for section in sections
    ]

    if portfolio_description.resume_path is not None:
        new_resume_path = static_content_directory.joinpath("resume").with_suffix(
            portfolio_description.resume_path.suffix
        )
        shutil.copy(
            src=portfolio_description_path.parent.joinpath(portfolio_description.resume_path),
            dst=new_resume_path,
        )
        resume_path = new_resume_path.name
    else:
        resume_path = None

    asset_image_processor = partial(
        render_local_media,
        static_content_directory,
        portfolio_description_path,
        None,
        images_sizes.large,
    )

    return Portfolio(
        title=portfolio_description.title,
        description=render_markdown(portfolio_description.description),
        sections=sections_with_entry_neighbors,
        conclusion=render_markdown(portfolio_description.conclusion),
        contact_urls=_render_link_list(portfolio_description.contact_urls),
        email=portfolio_description.email,
        explanation=render_markdown(portfolio_description.explanation),
        header_top_image=asset_image_processor(portfolio_description.header_top_image),
        header_bottom_image=asset_image_processor(portfolio_description.header_bottom_image),
        icon=render_local_media(
            media_directory=static_content_directory,
            yaml_path=portfolio_description_path,
            new_file_name="portfolio_icon.png",
            image_config=images_sizes.icon,
            local_media=portfolio_description.icon,
        ),
        resume_path=resume_path,
        portrait=asset_image_processor(portfolio_description.portrait),
        header_background=asset_image_processor(portfolio_description.header_background),
    )
