"""
Describes the data that make up the portfolio.
"""

import string
import typing as t
from datetime import date
from enum import Enum, IntEnum
from pathlib import Path
from typing import List, Optional

from pyaml import yaml
from pydantic import BaseModel, EmailStr, HttpUrl, ValidationError
from pydantic.color import Color
from spellchecker import SpellChecker
from typing_extensions import TypedDict

GLOBAL_CHECKER = SpellChecker()


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

    social = "social"


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
    protoboard_electronics = "protoboard electronics"
    pcb_electronics = "pcb electronics"
    electrical_cad = "electrical cad"
    mechanical_cad = "mechanical cad"
    c_sharp = "c#"
    python = "python"
    raspberry_pi = "raspberry pi"
    led_art = "led art"
    twitter = "twitter"
    frontend_web_development = "frontend web development"
    photography = "photography"
    events = "events"
    apparel = "apparel"
    artificial_intelligence = "artificial intelligence"


class TeamSize(str, Enum):
    """
    Describes how big the team working on the portfolio item was.
    """

    solo = "solo"
    small_group = "small group"
    large_group = "large group"


def clean_and_split(value: str) -> t.List[str]:
    """
    Cleans up the given label or entry or description, returns the resulting words for
    spell checking. Tries to intelligently replace punctuation.
    :return: List of words in a given piece of text.
    """

    become_spaces = ["-", "/"]
    delete = [character for character in string.punctuation if character not in become_spaces]
    deleted = value.translate({ord(character): "" for character in delete})
    spaced = deleted.translate(str.maketrans("".join(become_spaces), " " * len(become_spaces)))
    lower_case = spaced.lower()

    return lower_case.split(" ")


class ValidatedString(str):
    """
    Pydantic runs __get_validators__ upon loading a string.
    This:
        * Makes sure the input ends with a period.
        * Warns any words that could potentially be misspelled.
    """

    @classmethod
    def __get_validators__(  # type: ignore[misc]
        cls: "ValidatedString",
    ) -> t.Iterator[t.Callable[[str], str]]:
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield from [cls.ends_with_period, cls.warn_on_misspelling]

    def ends_with_period(  # pylint: disable=no-self-argument,no-self-use
        cls: "ValidatedString", value: str
    ) -> str:
        """
        Individual pieces of text must end with a period.
        :param value: To check.
        :return: `value` if there are no errors.
        :raises: `ValueError` if the given check fails.
        """

        if not value.endswith("."):
            raise ValueError("Descriptions must end with a period!")

        return value

    def warn_on_misspelling(  # pylint: disable=no-self-argument,no-self-use
        cls: "ValidatedString",
        value: str,
    ) -> str:
        """
        Logs potential spelling mistakes.
        :param value: To check.
        :return: `value`.
        """

        # find those words that may be misspelled
        misspelled = GLOBAL_CHECKER.unknown(clean_and_split(value))

        for word in misspelled:
            # TODO: want logger here eventually.
            print(f"misspelling? [{word}] in [{value}]")

        return value


class LocalMedia(TypedDict):
    """
    Describes a piece of media that is local to the repository ie NOT on the web.
    These images/gifs are copied from their entry directories to the `static` section of the
    flask application.
    """

    # Should be short, a description of what is in the piece of media.
    label: ValidatedString

    # Path relative to the YAML referencing it.
    path: Path


class Link(TypedDict):
    """
    Add context to a link on the web.
    These two are merged together in the portfolio to give the reader some context.
    """

    # A sentence saying where the link is going. Ex: "This project was featured on RaspberryPi.org"
    label: ValidatedString

    # The actual link.
    link: HttpUrl


class YouTubeVideo(TypedDict):
    """
    Identifies a YouTube video to be embedded in the portfolio entry.
    """

    # A sentence describing what the video is of.
    label: ValidatedString

    # The YouTube video ID, used later to create an iframe.
    video_id: str


class SerializedEntry(BaseModel):
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
    description: ValidatedString

    # Between three and five sentences, combined with the `description`, should give reader a very
    # complete idea as to what the project was about.
    explanation: ValidatedString

    # Best image (piece of media) representation of the entry. Will be featured on the overview
    # page and on the top of the entry page.
    featured_media: LocalMedia

    # Key pieces of media to describe the project. Shouldn't be too many.
    local_media: Optional[List[LocalMedia]]

    # Videos from YouTube can also be embedded into the portfolio renderings.
    youtube_videos: Optional[List[YouTubeVideo]]

    # See type docs.
    size: EntrySize

    # See type docs.
    domain: Domain

    # Instead of a description here, this should be a call to action. Ex: "Check out the blog post"
    primary_url: Link

    # URLs that are associated with the entry, but not as "important" as the primary. Ex:
    # In the Tesla Cooler entry, the blog post on esologic.com is the primary url, but links to the
    # project's github ETC are secondary links
    secondary_urls: Optional[List[Link]]

    # If the project was written about on Hackaday for example, those links should go here.
    press_urls: Optional[List[Link]]

    # Format `YYYY-MM-DD`
    completion_date: date

    # See type docs.
    team_size: TeamSize

    # Explanation as to my level of involvement on the project.
    # Team lead, solo developer, group of people etc.
    # One or two sentences at most.
    involvement: ValidatedString

    # See type docs.
    mediums: List[Medium]

    # If True, the item will be listed in the portfolio, if False it will be omitted.
    visible: bool


class SerializedSectionDescription(BaseModel):
    """
    Top level description of a whole section (meaning a group of entries like esologic, telapush
    etc) of entries. Note that the entries themselves are discovered by virtue of the directory
    structure and are not explicit listed in these files.
    # TODO, may want a logo here
    """

    # Name of the portfolio section, should be as short as possible to describe the section.
    title: str

    # A short description of the section, should be one or two sentences at the most.
    description: ValidatedString

    # See type docs.
    version_number: VersionNumber

    # CSS color, used to set the background of the section.
    primary_color: Color

    # Relative path to a logo for this section
    logo: LocalMedia

    # Controls the presentation order of the different sections. Lower numbers are ranked higher
    # and will appear first.
    rank: int


class SerializedPortfolioDescription(BaseModel):
    """
    Description of entire portfolio.
    """

    # Main header of the portfolio. Should be something like: "Collected works of Devon Bray"
    title: str

    # Can add a note about why projects were selected, probably want to go over nature of day job
    description: ValidatedString

    # See type docs.
    version_number: VersionNumber

    explanation: ValidatedString

    conclusion: ValidatedString

    email: EmailStr

    contact_urls: t.List[Link]

    header_top_image: LocalMedia

    header_bottom_image: LocalMedia

    return_image: LocalMedia

    icon: LocalMedia


def read_yaml(path: Path) -> t.Dict[str, t.Any]:  # type: ignore[misc]
    """
    Read a yaml to a dict. Schema is going to get verified later don't worry.
    :param path: Path to the yaml on disk.
    :return: Dict representation of yaml
    """

    with open(path) as f:
        return dict(yaml.load(f, Loader=yaml.FullLoader))


@t.overload
def read_portfolio_element(
    yaml_path: Path, element_type: t.Type[SerializedEntry]
) -> SerializedEntry:
    ...


@t.overload
def read_portfolio_element(
    yaml_path: Path, element_type: t.Type[SerializedSectionDescription]
) -> SerializedSectionDescription:
    ...


@t.overload
def read_portfolio_element(
    yaml_path: Path, element_type: t.Type[SerializedPortfolioDescription]
) -> SerializedPortfolioDescription:
    ...


def read_portfolio_element(
    yaml_path: Path,
    element_type: t.Union[
        t.Type[SerializedEntry],
        t.Type[SerializedSectionDescription],
        t.Type[SerializedPortfolioDescription],
    ],
) -> t.Union[SerializedEntry, SerializedSectionDescription, SerializedPortfolioDescription]:
    """
    Read the yaml file from disk and convert it to the desired structure.
    :param yaml_path: Path to the yaml file on disk.
    :param element_type: The type of the object described by the yaml file.
    :return: The loaded object.
    """
    try:
        return element_type(**read_yaml(yaml_path))
    except ValidationError as e:
        raise ValueError(
            f"Couldn't validate to schema: {element_type.__name__} file: {str(yaml_path)}"
        ) from e
