"""
Interface through which other components of this application access the content of the portfolio.
"""

import string
import typing as t
from datetime import date
from pathlib import Path
from typing import NamedTuple

from devon_bray_portfolio.content.schema import (
    LabeledLink,
    Medium,
    SerializedEntry,
    SerializedSectionDescription,
    read_portfolio_element,
)

YAML_EXTENSION = "yaml"


class LinkParts(NamedTuple):
    """
    Easy to render TODO: fill this out more
    """

    label: str
    link: str


class MediaParts(NamedTuple):
    """
    Easy to render TODO: fill this out more
    """

    label: str
    path: str


class Entry(NamedTuple):
    """
    Easy to render TODO: fill this out more
    """

    slug: str
    title: str
    description: str
    explanation: str
    gallery: t.List[t.Union[LinkParts, MediaParts]]
    size: str
    domain: str
    primary_url: LinkParts
    secondary_urls: t.Optional[t.List[LinkParts]]
    press_urls: t.Optional[t.List[LinkParts]]
    completion_date: str
    team_size: str
    involvement: str
    mediums: t.List[str]


class Section(NamedTuple):
    """
    Read from disk into memory
    Contains the entries that make up a whole section of the portfolio. Ex: Telapush, esologic
    Note: These could be written by hand but that would kind of complicate things.
    TODO - think more about this
    """

    title: str
    description: str
    primary_url: LinkParts
    entries: t.List[Entry]


def convert_url(url: LabeledLink) -> LinkParts:
    """
    TODO
    :param url:
    :return:
    """
    return LinkParts(label=url["label"], link=str(url["link"]))  # just a plain string now


def read_entry(yaml_path: Path, media_directory: Path) -> Entry:  # pylint: disable=unused-argument
    """

    :param yaml_path:
    :param media_directory:
    :return:
    """

    serialized_entry = read_portfolio_element(yaml_path, SerializedEntry)

    def render_date(d: date) -> str:
        return d.strftime("%B of %Y")

    def render_mediums(mediums: t.List[Medium]) -> t.List[str]:
        """
        TODO: this can assuredly be implemented more pythonically.
        :param mediums:
        :return:
        """

        def convert(medium: str) -> str:
            for bad, good in [("3d", "3D"), ("Cad", "CAD")]:
                if bad in medium:
                    return medium.replace(bad, good)

            return medium

        return [convert(medium) for medium in [string.capwords(medium) for medium in mediums]]

    def render_url_list(url_list: t.Optional[t.List[LabeledLink]]) -> t.Optional[t.List[LinkParts]]:
        """

        :param url_list:
        :return:
        """

        return [convert_url(url) for url in url_list] if url_list else None

    return Entry(
        slug=yaml_path.with_suffix("").name,
        title=serialized_entry.title,
        description=serialized_entry.description,
        explanation=serialized_entry.explanation,
        gallery=None,
        size=serialized_entry.size.value,
        domain=string.capwords(serialized_entry.domain.value),
        primary_url=convert_url(serialized_entry.primary_url),
        secondary_urls=render_url_list(serialized_entry.secondary_urls),
        press_urls=render_url_list(serialized_entry.press_urls),
        completion_date=render_date(serialized_entry.completion_date),
        team_size=string.capwords(serialized_entry.team_size.value),
        involvement=serialized_entry.involvement,
        mediums=render_mediums(serialized_entry.mediums),
    )


def find_yaml(directory: Path) -> Path:
    """

    :param directory:
    :return:
    """

    yaml_paths = list(directory.glob(f"*.{YAML_EXTENSION}"))

    if len(yaml_paths) > 1:
        raise ValueError(f"Found too many yaml files in dir: {directory}")

    return next(iter(yaml_paths))


def directories_in_directory(directory: Path) -> t.Iterator[Path]:
    """
    For the given directory, yield paths to directories within that directory.
    :param directory: Path to search
    :return: Sub directories, is not recursive.
    """

    yield from [path for path in directory.iterdir() if path.is_dir()]


def read_section(section_directory: Path, static_content_directory: Path) -> Section:
    """

    :param section_directory:
    :return:
    """

    section_description_path = find_yaml(section_directory)
    section_description = read_portfolio_element(
        section_description_path, SerializedSectionDescription
    )

    return Section(
        description=section_description.description,
        title=section_description.title,
        primary_url=convert_url(section_description.primary_url),
        entries=[
            read_entry(find_yaml(path), static_content_directory)
            for path in directories_in_directory(section_directory)
        ],
    )


def discover_portfolio(sections_directory: Path, static_content_directory: Path) -> t.List[Section]:
    """
    Reads all of the available entries from the content folder into their in-memory forms and
    returns them.
    :return: The list of entries.
    """

    return [
        read_section(section_directory, static_content_directory)
        for section_directory in directories_in_directory(sections_directory)
    ]
