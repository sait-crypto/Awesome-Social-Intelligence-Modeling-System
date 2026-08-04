# Contributing

Thank you for helping maintain the Social Intelligence Modeling paper collection.

## Before submitting

- Check both `README.md` and `COMPLETE_LIST.md` for an existing record.
- Use the taxonomy defined in `engineering/config/categories_config.py`.
- Prefer stable publisher, DOI, ACL Anthology, OpenReview, CVF, or arXiv links.
- Do not add local paper PDFs. The repository stores metadata and selected pipeline images, not manuscript copies.

## Recommended workflow

1. Install the project environment with `uv sync`.
2. Run `uv run submit.py` to open the submission interface.
3. Add or edit paper metadata. Fields marked with `*` are required.
4. If a pipeline image is needed, import it through the interface. It will be stored under `engineering/assets/<paper-uid>/`.
5. Save the update as `submit_template.json` or `submit_template.csv`.
6. Validate the submission with `uv run engineering/scripts/validate_submission.py`.
7. Open a pull request containing the update file and any referenced images.

## Manual submissions

You may edit `submit_template.json` directly. Keep array-valued fields in the documented format, use taxonomy `unique_name` values for categories, and do not include local absolute paths, credentials, cache files, database backups, or paper PDFs.

## Pull request checklist

- Metadata is in English.
- The paper is in scope for Social Intelligence Modeling.
- Paper and project URLs resolve correctly.
- Categories are supported by the paper's actual task and contribution.
- Referenced images exist under `engineering/assets/<paper-uid>/`.
- Generated files and tests pass.

For help, email [lixiajie2182712226@gmail.com](mailto:lixiajie2182712226@gmail.com).
