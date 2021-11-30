"""
Functionality for dealing with images and media to be included in portfolio.
Creating entries should be as simple as possible, and they should contain the maxiumum amount
of data for the project. Therefore, images should be huge when added to content, and then
compressed for rendering on the web.
"""

import typing as t
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageOps, ImageSequence

from devon_bray_portfolio.content_api import schema
from devon_bray_portfolio.content_api.markdown_render import render_markdown


class RenderedLocalMedia(NamedTuple):
    """
    Derived from the `LocalMedia` TD in `schema.py`.
    All string fields, this structure will be directly input into the jinja html template
    by flask.
    """

    label: str
    path: str


class ImageConfig(NamedTuple):
    """
    Describes how an individual image is to be modified for inclusion in the portfolio.
    """

    max_dimensions: t.Tuple[int, int]

    # Passed to the `save` parameter in PIL.
    quality: int

    # If given, all images will be re-created upon load.
    force_rewrite: bool


def render_local_media(
    media_directory: Path,
    yaml_path: Path,
    new_file_name: t.Optional[str],
    image_config: ImageConfig,
    local_media: schema.LocalMedia,
) -> RenderedLocalMedia:
    """
    Copies, processes images from their origins in the entry folders to their destinations
    in the `media_directory` folder. Returns a new NT, with a reference to their path
    relative to `media_directory`.
    :param media_directory: Destination path parent.
    :param yaml_path: Config file image was read from.
    :param new_file_name: Filename of output, by default will have the same name
    as given.
    :param image_config: Describes transformations that should be made to the image
    before copying to output.
    :param local_media: To copy.
    :return: For addition to portfolio.
    """

    name = local_media["path"].name if new_file_name is None else new_file_name
    output_path = media_directory.joinpath(name)

    if not output_path.exists() or image_config.force_rewrite:

        image = Image.open(str(yaml_path.parent.joinpath(local_media["path"])))

        if getattr(image, "is_animated", False):

            frames = ImageSequence.Iterator(image)

            # Wrap on-the-fly thumbnail generator
            def thumbnails(f: ImageSequence.Iterator) -> t.Iterator[Image.Image]:
                for frame in f:
                    thumbnail = frame.copy()
                    thumbnail.thumbnail(image_config.max_dimensions, Image.ANTIALIAS)
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

            respect_rotation.thumbnail(image_config.max_dimensions, Image.ANTIALIAS)
            respect_rotation.save(str(output_path), quality=image_config.quality)

    return RenderedLocalMedia(label=render_markdown(local_media["label"]), path=str(name))


class ImagesConfig(NamedTuple):
    """
    Describes how images are to be modified for inclusion in the portfolio.
    This is exposed by the API to be filled by a human.
    TODO: Could include this in one of the yamls.
    """

    # Images that will be displayed largely. Portrait, in portfolio entries, in main header
    # etc, will be scaled to fit within this bounding box.
    large_image_max_dimensions: t.Tuple[int, int]

    # Images that will be displayed in small forms only, like the back button on the entry
    # page will be scaled to fit within this bounding box.
    small_image_max_dimensions: t.Tuple[int, int]

    # When images are turned into favicons, they will be scaled to fit within this bounding box.
    icon_max_dimensions: t.Tuple[int, int]

    # Passed to the `save` parameter in PIL.
    quality: int

    # If given, all images will be re-created upon load.
    force_rewrite: bool


class ImageSizes(NamedTuple):
    """
    Lists the options for images to make selection easier.
    """

    large: ImageConfig
    small: ImageConfig
    icon: ImageConfig


def unpack_image_sizes(images_config: ImagesConfig) -> ImageSizes:
    """
    Unpacks the user-facing ImagesConfig to sets of sizes to be consumed by portfolio engine.
    :param images_config: From user.
    :return: NT
    """

    return ImageSizes(
        large=ImageConfig(
            max_dimensions=images_config.large_image_max_dimensions,
            quality=images_config.quality,
            force_rewrite=images_config.force_rewrite,
        ),
        small=ImageConfig(
            max_dimensions=images_config.small_image_max_dimensions,
            quality=images_config.quality,
            force_rewrite=images_config.force_rewrite,
        ),
        icon=ImageConfig(
            max_dimensions=images_config.icon_max_dimensions,
            quality=images_config.quality,
            force_rewrite=images_config.force_rewrite,
        ),
    )
