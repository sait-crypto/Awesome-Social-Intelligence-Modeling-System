import os

from src.utils import normalize_pipeline_image, validate_pipeline_image


def test_normalize_with_absolute_figure_dir_and_abs_path():
    fig_dir = r"C:\repo\figures"
    path = r"C:\images\LIN.png"
    assert normalize_pipeline_image(path, fig_dir) == "figures/LIN.png"


def test_validate_accepts_lin_png_with_absolute_figdir():
    fig_dir = r"C:\repo\figures"
    valid, normalized = validate_pipeline_image("LIN.png", fig_dir)
    assert valid is True
    assert normalized == "figures/LIN.png"


def test_normalize_keeps_relative_path():
    assert normalize_pipeline_image("figures/LIN.png", "figures") == "figures/LIN.png"


def test_validate_rejects_non_image_extension():
    valid, normalized = validate_pipeline_image("LIN.txt", "figures")
    assert valid is False
    assert normalized.endswith("LIN.txt")


def test_validate_accepts_multiple_images():
    fig_dir = r"C:\repo\figures"
    valid, normalized = validate_pipeline_image("LIN.png; other.jpg", fig_dir)
    assert valid is True
    assert normalized == "figures/LIN.png;figures/other.jpg"


def test_validate_rejects_more_than_three_images():
    fig_dir = "figures"
    valid, normalized = validate_pipeline_image("a.png; b.png; c.png; d.png", fig_dir)
    assert valid is False
    # normalized should contain the first three normalized entries
    assert normalized == "figures/a.png;figures/b.png;figures/c.png"
