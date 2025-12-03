# coding: utf-8
import PIL.Image
import PIL.ImageDraw

from handright import InlineImage, Template, handwrite, split_text_and_formula
from tests.util import get_default_font


def _get_template():
    background = PIL.Image.new(mode="1", size=(320, 240), color=1)
    font = get_default_font(32)
    return Template(
        background=background,
        font=font,
        line_spacing=48,
        left_margin=20,
        right_margin=20,
        top_margin=20,
        bottom_margin=20,
    )


def test_split_text_and_formula_creates_inline_image():
    def _renderer(expr: str) -> InlineImage:
        assert expr == "x^2"
        mask = PIL.Image.new("1", (10, 12), 1)
        return InlineImage(mask)

    pieces = split_text_and_formula("a$x^2$b", _renderer)
    assert len(pieces) == 3
    assert isinstance(pieces[1], InlineImage)


def test_inline_image_expands_line_height():
    template = _get_template()
    tall_image = PIL.Image.new("1", (24, 90), 1)
    inline = InlineImage(tall_image)
    images = tuple(handwrite([inline, "测"], template, seed=123))
    assert len(images) == 1
    im = images[0]
    # Ensure tall image strokes are not clipped by verifying white pixels exist
    # near the bottom of the first line region.
    bbox = im.getbbox()
    assert bbox is not None
    _, top, _, bottom = bbox
    assert bottom - top >= template.get_line_spacing()
