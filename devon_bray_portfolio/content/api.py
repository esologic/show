"""
Interface through which other components of this application access the content of the portfolio.
"""

import typing as t
from pathlib import Path

import yaml
from pydantic.error_wrappers import ValidationError

from devon_bray_portfolio.content.schema import PortfolioEntry, PortfolioSection, SectionDescription

YAML_EXTENSION = "yaml"


def read_yaml(path: Path) -> t.Dict[str, t.Any]:  # type: ignore[misc]
    """
    Read a yaml to a dict. Schema is going to get verified later don't worry.
    :param path: Path to the yaml on disk.
    :return: Dict representation of yaml
    """

    with open(path) as f:
        return dict(yaml.load(f, Loader=yaml.FullLoader))


@t.overload
def read_portfolio_element(yaml_path: Path, element_type: t.Type[PortfolioEntry]) -> PortfolioEntry:
    ...


@t.overload
def read_portfolio_element(
    yaml_path: Path, element_type: t.Type[SectionDescription]
) -> SectionDescription:
    ...


def read_portfolio_element(
    yaml_path: Path, element_type: t.Union[t.Type[PortfolioEntry], t.Type[SectionDescription]]
) -> t.Union[PortfolioEntry, SectionDescription]:
    """

    :param yaml_path:
    :param element_type:
    :return:
    """
    try:
        return element_type(**read_yaml(yaml_path))
    except ValidationError as e:
        raise ValueError(
            f"Couldn't validate to schema: {element_type.__name__} file: {str(yaml_path)}"
        ) from e


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


def read_section(section_directory: Path) -> PortfolioSection:
    """

    :param section_directory:
    :return:
    """

    section_description_path = find_yaml(section_directory)
    section_description = read_portfolio_element(section_description_path, SectionDescription)

    entries: t.List[PortfolioEntry] = [
        read_portfolio_element(find_yaml(path), PortfolioEntry)
        for path in directories_in_directory(section_directory)
    ]

    return PortfolioSection(
        description=section_description.description,
        title=section_description.title,
        primary_url=section_description.primary_url,
        entries=entries,
    )


def discover_sections(sections_directory: Path) -> t.List[PortfolioSection]:
    """
    Reads all of the available entries from the content folder into their in-memory forms and
    returns them.
    :return: The list of entries.
    """

    return [
        read_section(section_directory)
        for section_directory in directories_in_directory(sections_directory)
    ]
