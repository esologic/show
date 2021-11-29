"""
Interface through which other components of this application access the content of the portfolio.
TODO: There's a bit of redundancy, and a little more inheritance could be helpful.
"""
import itertools
import shutil
import string
import typing as t
from datetime import date
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple

from markdown import markdown
from PIL import Image, ImageOps, ImageSequence

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


def _render_markdown(text: str) -> str:
    """

    :param text:
    :return:
    """

    return markdown(text, extensions=["markdown3_newtab"])


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
        sorted([convert(medium) for medium in [string.capwords(medium) for medium in mediums]])
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


def _render_local_media(
    media_directory: Path,
    yaml_path: Path,
    max_size: t.Tuple[int, int],
    output_name: t.Optional[str],
    force_recreate: bool,
    local_media: schema.LocalMedia,
) -> RenderedLocalMedia:
    """
    Copies, processes images from their origins in the entry folders to their destinations
    in the `media_directory` folder. Returns a new NT, with a reference to their path
    relative to `media_directory`.
    :param media_directory: Destination path parent.
    :param yaml_path: Config file image was read from.
    :param max_size: Max image size in pixels.
    :param output_name: Filename of output
    :param local_media: To copy.
    :param force_recreate: Force a recompute.
    :return: For addition to portfolio.
    """

    name = local_media["path"].name if output_name is None else output_name
    output_path = media_directory.joinpath(name)

    if not output_path.exists() or force_recreate:

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
            respect_rotation = ImageOps.exif_transpose(image)
            if respect_rotation.mode == "RGBA":
                background = Image.new("RGBA", respect_rotation.size, (0, 0, 0))
                respect_rotation = Image.alpha_composite(background, respect_rotation)
                respect_rotation = respect_rotation.convert("RGB")

            respect_rotation.thumbnail(max_size)

            respect_rotation.save(str(output_path))

    return RenderedLocalMedia(label=_render_markdown(local_media["label"]), path=str(name))


def _read_entry_from_disk(
    yaml_path: Path,
    media_directory: Path,
    primary_color: str,
    top_image: RenderedLocalMedia,
    write_images: bool,
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
        _render_local_media, media_directory, yaml_path, (3000, 3000), None, write_images
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
            RenderedYouTubeVideo(label=_render_markdown(video["label"]), video_id=video["video_id"])
            for video in serialized_entry.youtube_videos
        )
        if serialized_entry.youtube_videos is not None
        else None
    )

    return RenderedEntryWithoutNeighbors(
        slug=slug,
        title=serialized_entry.title,
        description=serialized_entry.description,
        explanation=_render_markdown(serialized_entry.explanation),
        featured_media=media_processor(serialized_entry.featured_media),
        local_media=local_media,
        youtube_videos=youtube_videos,
        size=serialized_entry.size.value,
        domain=string.capwords(serialized_entry.domain.value),
        primary_url=_render_link(serialized_entry.primary_url),
        secondary_urls=_render_link_list(serialized_entry.secondary_urls),
        press_urls=_render_link_list(serialized_entry.press_urls),
        completion_date=serialized_entry.completion_date,
        completion_date_verbose=_render_date(serialized_entry.completion_date, verbose=True),
        completion_year=_render_date(serialized_entry.completion_date, verbose=False),
        team_size=string.capwords(serialized_entry.team_size.value),
        involvement=serialized_entry.involvement,
        mediums=_render_mediums(serialized_entry.mediums),
        primary_color=primary_color,
        favicon_path=_render_local_media(
            media_directory,
            yaml_path,
            (50, 50),
            f"{slug}_icon.png",
            write_images,
            serialized_entry.featured_media,
        ).path,
        top_image=top_image,
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
    top_image: RenderedLocalMedia,
    write_images: bool,
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
                    _find_yaml(path),
                    static_content_directory,
                    primary_color,
                    top_image,
                    write_images,
                )
                for path in _directories_in_directory(section_directory)
            ],
            key=lambda entry: entry.completion_date,
            reverse=True,
        )
    )

    return SectionIncompleteEntries(
        description=_render_markdown(section_description.description),
        title=section_description.title,
        entries=entries,
        primary_color=primary_color,
        logo=_render_local_media(
            static_content_directory,
            section_description_path,
            (500, 500),
            None,
            write_images,
            section_description.logo,
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
    sections_directory: Path, static_content_directory: Path, write_images: bool
) -> Portfolio:
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

    sections = sorted(
        [
            _read_section_from_disk(
                section_directory,
                static_content_directory,
                _render_local_media(
                    static_content_directory,
                    portfolio_description_path,
                    (4000, 4000),
                    None,
                    write_images,
                    portfolio_description.return_image,
                ),
                write_images=write_images,
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

    return Portfolio(
        title=portfolio_description.title,
        description=_render_markdown(portfolio_description.description),
        sections=sections_with_entry_neighbors,
        conclusion=_render_markdown(portfolio_description.conclusion),
        contact_urls=_render_link_list(portfolio_description.contact_urls),
        email=portfolio_description.email,
        explanation=_render_markdown(portfolio_description.explanation),
        header_top_image=_render_local_media(
            static_content_directory,
            portfolio_description_path,
            (4000, 4000),
            None,
            write_images,
            portfolio_description.header_top_image,
        ),
        header_bottom_image=_render_local_media(
            static_content_directory,
            portfolio_description_path,
            (4000, 4000),
            None,
            write_images,
            portfolio_description.header_bottom_image,
        ),
        icon=_render_local_media(
            static_content_directory,
            portfolio_description_path,
            (50, 50),
            None,
            write_images,
            portfolio_description.icon,
        ),
        resume_path=resume_path,
        portrait=_render_local_media(
            static_content_directory,
            portfolio_description_path,
            (3000, 3000),
            None,
            write_images,
            portfolio_description.portrait,
        ),
        header_background=_render_local_media(
            static_content_directory,
            portfolio_description_path,
            (3000, 3000),
            None,
            write_images,
            portfolio_description.header_background,
        ),
    )
