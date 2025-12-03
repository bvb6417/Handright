# coding: utf-8
"""Rich text helpers for Handright."""
from __future__ import annotations
import importlib.util
import io
from dataclasses import dataclass
from typing import Callable, List, Tuple, Union

import PIL.Image

__all__ = ["InlineImage", "split_text_and_formula", "docx_to_contents"]


@dataclass
class InlineImage(object):
    """Represents an inline image in a text stream."""

    image: PIL.Image.Image
    target_height: int | None = None

    def get_image(self, target_height: int | None = None) -> PIL.Image.Image:
        height = self.target_height or target_height
        if height is None:
            return self.image
        width, original_height = self.image.size
        if original_height == height:
            return self.image
        ratio = height / original_height
        return self.image.resize(
            (max(1, round(width * ratio)), height),
            resample=PIL.Image.LANCZOS,
        )

    @classmethod
    def from_latex(
            cls,
            formula: str,
            *,
            dpi: int = 300,
            font_size: int = 16,
            padding: float = 0.1,
            color: str = "black",
            target_height: int | None = None,
    ) -> "InlineImage":
        """Render a LaTeX expression to an image.

        The background is transparent so it can be pasted onto the binary mask
        that Handright uses internally.
        """
        if importlib.util.find_spec("matplotlib") is None:
            raise ImportError("matplotlib is required for InlineImage.from_latex")
        import matplotlib.pyplot as plt

        plt.switch_backend("Agg")
        fig = plt.figure()
        text = fig.text(0, 0, f"${formula}$", fontsize=font_size, color=color)
        fig.canvas.draw()
        bbox = text.get_window_extent()
        width_in, height_in = (
            bbox.width / dpi,
            bbox.height / dpi,
        )
        fig.set_size_inches((width_in, height_in))
        fig.canvas.draw()
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            transparent=True,
            bbox_inches="tight",
            pad_inches=padding,
        )
        plt.close(fig)
        buf.seek(0)
        image = PIL.Image.open(buf)
        return cls(image=image.convert("RGBA"), target_height=target_height)


ContentPiece = Union[str, InlineImage]


def split_text_and_formula(
        text: str,
        formula_renderer: Callable[[str], InlineImage],
) -> List[ContentPiece]:
    """Split text with ``$...$`` math delimiters into text and :class:`InlineImage`.

    ``formula_renderer`` is only called for content wrapped in ``$`` markers.
    Unbalanced markers are treated as plain text.
    """
    pieces: List[ContentPiece] = []
    segments = text.split("$")
    for index, segment in enumerate(segments):
        if index % 2 == 1:
            pieces.append(formula_renderer(segment))
        else:
            pieces.extend(segment)
    if len(segments) % 2 == 0:
        pieces.append("$")
    return pieces


def docx_to_contents(
        path: str,
        *,
        formula_renderer: Callable[[str], InlineImage],
        indent_fallback: int = 2,
) -> Tuple[ContentPiece, ...]:
    """Convert a docx file into a sequence usable by :func:`handwrite`.

    The function keeps the first-line indentation from the paragraph settings
    by translating it into spaces and replaces ``$...$`` math blocks with
    rendered images.
    """
    if importlib.util.find_spec("docx") is None:
        raise ImportError("python-docx is required to parse docx files")
    from docx import Document

    document = Document(path)
    contents: List[ContentPiece] = []
    for paragraph in document.paragraphs:
        indent_spaces = _indent_as_spaces(paragraph, fallback=indent_fallback)
        if indent_spaces:
            contents.extend(" " * indent_spaces)
        contents.extend(split_text_and_formula(paragraph.text, formula_renderer))
        contents.append("\n")
    return tuple(contents)


def _indent_as_spaces(paragraph, fallback: int) -> int:
    first_line = paragraph.paragraph_format.first_line_indent
    if first_line is None:
        return 0
    font_size = None
    if paragraph.style is not None and paragraph.style.font is not None:
        font_size = paragraph.style.font.size
    for run in paragraph.runs:
        if run.font.size is not None:
            font_size = run.font.size
            break
    if font_size is None:
        return fallback
    return max(round(first_line.pt / font_size.pt), 0)
