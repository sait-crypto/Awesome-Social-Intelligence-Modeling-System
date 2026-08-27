# Survey Website Maintenance

The public survey website is a generated view of the repository, not a second paper database.

## Source of truth

- Selected papers: `engineering/paper_database_for_survey.csv`
- Taxonomy: `engineering/config/categories_config.py`
- Survey metadata: `engineering/config/paper_metadata.json`
- Static page source: `site/`
- Generated deployment directory: `site-dist/` (ignored by Git)

Run the local build from the repository root:

```text
python engineering/scripts/build_site.py --output site-dist
python -m http.server 8765 --directory site-dist
```

The build copies only the required framework images and writes `assets/data/site-data.json`. Do not edit the generated JSON by hand.

## GitHub Pages

`.github/workflows/deploy_pages.yml` builds pull requests for validation and deploys every accepted `main` update that changes the website, selected database, taxonomy, metadata, or required images.

One repository administrator must select **Settings → Pages → Build and deployment → GitHub Actions** once. The expected project URL is:

```text
https://sait-crypto.github.io/Awesome-Social-Intelligence-Modeling-System/
```

The paper-processing commit must not contain GitHub's `[skip ci]` marker because that would suppress the Pages rebuild.

## Community paper intake

One repository administrator must enable **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**. Without this setting, the reviewed issue cannot be converted into the processing pull request.

1. The homepage form or `.github/ISSUE_TEMPLATE/paper_submission.yml` creates a structured public issue.
2. A maintainer reviews scope and taxonomy and applies the existing `Action: Process` label.
3. `.github/workflows/intake_paper_issue.yml` converts the issue to `submit_template.json`, preserves the GitHub author in `contributor`, validates it, and opens a processing pull request.
4. The intake workflow explicitly calls the existing `Process Paper Submission` reusable workflow for that pull request. This avoids relying on a `GITHUB_TOKEN`-created pull-request event to start a second workflow.
5. The database commit triggers the Pages workflow.

The homepage accepts the standard single-item JSON produced by `AI_assistant_review_tools/tools/One-Click Copy Metadata.xpi`. It maps Zotero title, creators, DOI, date, URL, abstract, venue, citation key, and supported `cat ...` tags into the form; taxonomy remains reviewable before submission.

Remove and reapply `Action: Process` after correcting a failed issue intake. Do not add the label to unreviewed or spam issues.

### Contributor provenance

Only records accepted through the third-party intake mechanism use the explicit `community:` prefix in the `contributor` field:

```text
community:@github-login
```

The website and generated README display the Community badge only for this prefix. Existing records, including historical external-looking contributor values, remain part of the maintainer-curated collection and are not relabeled automatically.

## Failure email

Issue intake, paper processing, and GitHub Pages deployment can use these repository variables/secrets:

- Variables: `NOTIFICATION_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`
- Secret: `SMTP_PASSWORD`

Notification mail is sent from independent jobs so it can still run after intake, processing, or deployment fails. Failure subjects start with `🚨 [SIM AUTO UPDATE FAILED]`, and GitHub Pages failures explicitly state that repository data may have changed while the public site did not.

If SMTP is not configured, the notification step records that email was skipped. If SMTP is configured but delivery fails, the notification job fails visibly instead of silently swallowing the error.
