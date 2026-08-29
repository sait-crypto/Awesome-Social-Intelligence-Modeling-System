# Contributing

[← Back to main README](./README.md)

Thank you for helping maintain the Social Intelligence Modeling paper collection.

## Recommended workflow

For most contributors, use the **[website paper-submission form](https://sait-crypto.github.io/Awesome-Social-Intelligence-Modeling-System/#contribute)**. It can fill the required metadata from JSON copied by the repository's Zotero plugin, provides a hierarchical taxonomy selector, and prepares a structured public GitHub issue without collecting an email address. A maintainer reviews the scope and taxonomy, then applies the `Action: Process` label to that issue. The intake workflow creates a backend pull request and explicitly invokes the repository's existing paper-processing workflow, which validates the submission and updates the canonical databases. The accepted database commit then triggers one path-filtered website deployment.

Website submissions and submissions processed from a non-`main` pull request automatically receive a `community:` prefix in the paper's `contributor` field. Only this explicit prefix produces a **Community contribution** badge. Direct maintainer updates to `main` keep their existing provenance and are not marked as Community submissions.

The public suggestion issue is the primary communication record and remains open during review and processing. Waiting-for-approval status, validation and processing results, duplicate or rejection reasons, and maintainer feedback are posted there. The generated pull request is only a backend processing artifact. Subscribe to the GitHub issue to receive every update; maintainers should close it only after follow-up is complete. Do not place a private email address in the public form or in the paper database.

### Desktop and pull-request workflow

1. Install the project environment with `uv sync`, then run `uv run submit.py`, or double-click the root `Submit.exe` when available, to open the submission interface.
2. Add or edit paper metadata. Fields marked with `*` are required. ([Download the recommended Zotero plugin](https://raw.githubusercontent.com/sait-crypto/Awesome-Social-Intelligence-Modeling-System/main/AI_assistant_review_tools/tools/One-Click%20Copy%20Metadata.xpi) for one-click metadata copy from Zotero.)
3. If a pipeline image is needed, import it through the interface. It will be stored under `engineering/assets/<paper-uid>/`.
4. Save the update as `submit_template.json` or `submit_template.csv`.
5. You can validate the submission with the **Validate** button in the interface (`uv run engineering/scripts/validate_submission.py`).
6. Submit the update using either of these routes:
   - **Pull request (recommended):** Open a PR containing the update file and any referenced images. The repository Action can validate and process the submission automatically after permission from maintainer.
   - **Email fallback:** [Email me](mailto:lixiajie2182712226@gmail.com) with the completed `submit_template.json` or `submit_template.csv` file and any referenced files when GitHub submission is not possible.

> [!IMPORTANT]
> Pull requests must come from a non-`main` branch; submissions made directly from `main` do not trigger automatic processing.
>
> Relevant website, database, taxonomy, metadata, or build-script updates on `main` automatically rebuild GitHub Pages. This deployment workflow is separate from paper submission processing: an ordinary `main` push never starts the submission pipeline.

### If PR automation fails

The issue or pull request receives a visible failure comment with a link to the relevant workflow run. For pull-request submissions, the original update files are also preserved for 90 days in the `paper-submission-pr-<number>-<attempt>` workflow artifact, even when validation or database processing fails.

After correcting the structured fields, rerun the failed job or remove and reapply the `Action: Process` label. If the GitHub workflow remains blocked, use the email fallback above and include the preserved `submit_template` file plus the workflow-run link. Maintainer failure emails use the subject prefix `🚨 [SIM AUTO UPDATE FAILED]` so an unsuccessful database or website update is not mistaken for a completed one.

## Manual submissions  (not recommended)

You may edit `submit_template.json` directly. Keep array-valued fields in the documented format, use taxonomy `unique_name` values for categories, and do not include local absolute paths, credentials, cache files, database backups, or paper PDFs. (The taxonomy is defined in `engineering/config/categories_config.py`.)

## Pull request checklist

- Metadata is in English.
- The paper is in scope for Social Intelligence Modeling.
- Paper and project URLs resolve correctly.
- Categories are supported by the paper's actual task and contribution.
- Non-`main` pull requests are marked with `community:` automatically; direct maintainer updates on `main` retain their existing contributor value.
- Generated files and tests pass.

For help, [email me](mailto:lixiajie2182712226@gmail.com).
