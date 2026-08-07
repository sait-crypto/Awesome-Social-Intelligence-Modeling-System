# Contributing

[← Back to main README](./README.md)

Thank you for helping maintain the Social Intelligence Modeling paper collection.

## Before submitting

- Check both `README.md` and `COMPLETE_LIST.md` for an existing record.
- Use the taxonomy defined in `engineering/config/categories_config.py`.
- Prefer stable publisher, DOI, ACL Anthology, OpenReview, CVF, or arXiv links.
- Do not add local paper PDFs. The repository stores metadata and selected pipeline images, not manuscript copies.

## Recommended workflow

1. Install the project environment with `uv sync`, then run `uv run submit.py`, or double-click the root `Submit.exe` when available, to open the submission interface.
2. Add or edit paper metadata. Fields marked with `*` are required.
3. If a pipeline image is needed, import it through the interface. It will be stored under `engineering/assets/<paper-uid>/`.
4. Save the update as `submit_template.json` or `submit_template.csv`.
5. Validate the submission with `uv run engineering/scripts/validate_submission.py`.
6. Submit the update using either of these routes:
   - **Pull request:** Open a PR containing the update file and any referenced images. The repository Action can validate and process the submission automatically after permission from maintainer.
   - **Email:** [Email me](mailto:lixiajie2182712226@gmail.com) with the completed `submit_template.json` or `submit_template.csv` file and any referenced files.

> [!IMPORTANT]
> Pull requests must come from a non-`main` branch; submissions made directly from `main` do not trigger automatic processing.

## Manual submissions  (not recommended)

You may edit `submit_template.json` directly. Keep array-valued fields in the documented format, use taxonomy `unique_name` values for categories, and do not include local absolute paths, credentials, cache files, database backups, or paper PDFs.

## Pull request checklist

- Metadata is in English.
- The paper is in scope for Social Intelligence Modeling.
- Paper and project URLs resolve correctly.
- Categories are supported by the paper's actual task and contribution.
- Generated files and tests pass.

For help, [email me](mailto:lixiajie2182712226@gmail.com).
