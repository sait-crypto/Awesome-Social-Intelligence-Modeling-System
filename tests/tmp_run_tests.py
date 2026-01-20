from src.utils import normalize_pipeline_image, validate_pipeline_image

# test_normalize_with_absolute_figure_dir_and_abs_path
fig_dir = r"C:\repo\figures"
path = r"C:\images\LIN.png"
assert normalize_pipeline_image(path, fig_dir) == "figures/LIN.png"
# test_validate_accepts_lin_png_with_absolute_figdir
valid, normalized = validate_pipeline_image("LIN.png", fig_dir)
assert valid is True and normalized == "figures/LIN.png"
# test_normalize_keeps_relative_path
assert normalize_pipeline_image("figures/LIN.png", "figures") == "figures/LIN.png"
# test_validate_rejects_non_image_extension
valid, normalized = validate_pipeline_image("LIN.txt", "figures")
assert valid is False and normalized.endswith("LIN.txt")
# test_validate_accepts_multiple_images
fig_dir = r"C:\repo\figures"
valid, normalized = validate_pipeline_image("LIN.png; other.jpg", fig_dir)
assert valid is True and normalized == "figures/LIN.png;figures/other.jpg"
# test_validate_rejects_more_than_three_images
fig_dir = "figures"
valid, normalized = validate_pipeline_image("a.png; b.png; c.png; d.png", fig_dir)
assert valid is False and normalized == "figures/a.png;figures/b.png;figures/c.png"
print('ALL TESTS PASSED')
