"""
Describes the data that make up the portfolio.
"""

from datetime import date
from enum import Enum, IntEnum
from pathlib import Path
from typing import List, NamedTuple, Optional, Union

from pydantic import BaseModel, HttpUrl
from typing_extensions import TypedDict


class VersionNumber(IntEnum):
    """
    Contains the different possible versions of `PortfolioEntry` items.
    """

    version_0 = 0


class EntrySize(str, Enum):
    """
    Describes the scope of a portfolio item.
    Note, this will have a direct impact on the way that the piece of media is displayed to reader
    when rendered in the portfolio. `large` items will be visually larger than smaller sized items.
    """

    small = "small"
    medium = "medium"
    large = "large"


class Domain(str, Enum):
    """
    Describes the medium of a portfolio item.
    Note: I expect this list of options to get long, but that's fine.
    """

    # Index mount is an example of hardware
    hardware = "hardware"

    # Faces is an example of software, python_project is an example of software.
    software = "software"

    # Tesla Cooler is an example of mixed, CHAMP is an example of mixed.
    mixed_hardware_software = "mixed (hardware, software)"


class Medium(str, Enum):
    """
    The types of materials and technologies that make up the project.
    This enum is intentionally going to get large, but gives us a good way to have a consistent
    set of keywords across projects.
    """

    laser_cutter = "laser cutter"
    printer_3d = "3d printer"
    arduino = "arduino"
    fritzing = "fritzing"
    breadboard_electronics = "breadboard electronics"
    mechanical_cad = "mechanical cad"
    c_sharp = "c#"
    python = "python"
    raspberry_pi = "raspberry pi"


class TeamSize(str, Enum):
    """
    Describes how big the team working on the portfolio item was.
    """

    solo = "solo"
    group = "group"


class LabeledMedia(TypedDict):
    """
    Describes a piece of media.
    """

    # Should be short, a description of what is in the piece of media.
    label: str

    # Path to the piece of media within the repo.
    path: Path


class LabeledLink(TypedDict):
    """
    Add context to a link on the web.
    These two are merged together in the portfolio to give the reader some context.
    """

    # A sentence saying where the link is going. Ex: "This project was featured on RaspberryPi.org"
    label: str

    # The actual link.
    link: HttpUrl


class PortfolioEntry(BaseModel):
    """
    All of the raw data that makes up an entry in the portfolio.
    Note: The idea with this structure is that it can easily be written by hand using a markdown
    file that contains metadata yaml. The expectation is that these entries are written by hand.
    """

    # See type docs.
    version_number: VersionNumber

    # Name of the portfolio entry, should be as short as possible to describe the piece.
    title: str

    # A short description of the project, should be one or two sentences at the most.
    description: str

    # Between three and five sentences, combined with the `description`, should give reader a very
    # complete idea as to what the project was about.
    explanation: str

    # Key pieces of media (images or videos) to describe the project. Shouldn't be too many.
    gallery: List[Union[LabeledLink, LabeledMedia]]

    # See type docs.
    size: EntrySize

    # See type docs.
    domain: Domain

    # Instead of a description here, this should be a call to action. Ex: "Check out the blog post"
    primary_url: LabeledLink

    # URLs that are associated with the entry, but not as "important" as the primary. Ex:
    # In the Tesla Cooler entry, the blog post on esologic.com is the primary url, but links to the
    # project's github ETC are secondary links
    secondary_urls: Optional[List[LabeledLink]]

    # If the project was written about on Hackaday for example, those links should go here.
    press_urls: Optional[List[LabeledLink]]

    # Format `YYYY-MM-DD`
    completion_date: date

    # See type docs.
    team_size: TeamSize

    # Explanation as to my level of involvement on the project.
    # Team lead, solo developer, group of people etc.
    # One or two sentences at most.
    involvement: str

    # See type docs.
    mediums: List[Medium]


class SectionDescription(BaseModel):
    """
    Composed by hand
    # TODO, may want a logo here
    """

    # Name of the portfolio section, should be as short as possible to describe the section.
    title: str

    # A short description of the section, should be one or two sentences at the most.
    description: str

    # See type docs.
    version_number: VersionNumber

    # Instead of a description here, this should be a call to action. Ex: "Check out the blog post"
    primary_url: LabeledLink


class PortfolioSection(NamedTuple):
    """
    Read from disk into memory
    Contains the entries that make up a whole section of the portfolio. Ex: Telapush, esologic
    Note: These could be written by hand but that would kind of complicate things.
    TODO - think more about this
    """

    # Name of the portfolio section, should be as short as possible to describe the section.
    title: str

    # A short description of the section, should be one or two sentences at the most.
    description: str

    # Instead of a description here, this should be a call to action. Ex: "Check out the blog post"
    primary_url: LabeledLink

    # The entries that make up the individual portfolio section
    entries: List[PortfolioEntry]
