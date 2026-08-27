import importlib.util
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_ROOT = ROOT / "engineering"
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from src.convert import ReadmeGenerator
from src.core.database_manager import DatabaseManager
from src.core.database_model import Paper


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


build_site = load_module("build_site", "engineering/scripts/build_site.py")
issue_to_submission = load_module("issue_to_submission", "engineering/scripts/issue_to_submission.py")
download_issue_images = load_module("download_issue_images", "engineering/scripts/download_issue_images.py")
mark_community_submission = load_module("mark_community_submission", "engineering/scripts/mark_community_submission.py")
send_notification = load_module("send_notification", "engineering/scripts/send_notification.py")
validate_submission = load_module("validate_submission", "engineering/scripts/validate_submission.py")


class SurveyWebsiteBuildTests(unittest.TestCase):
    def test_build_produces_self_contained_site_from_selected_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site"
            data = build_site.build_site(output)
            stored = json.loads((output / "assets/data/site-data.json").read_text(encoding="utf-8"))
            complete = json.loads((output / "assets/data/complete-list-data.json").read_text(encoding="utf-8"))

            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "complete-list.html").is_file())
            self.assertTrue((output / "assets/css/styles.css").is_file())
            self.assertTrue((output / "assets/css/forms.css").is_file())
            self.assertTrue((output / "assets/css/complete-list.css").is_file())
            self.assertTrue((output / "assets/css/image-slots.css").is_file())
            self.assertTrue((output / "assets/js/app.js").is_file())
            self.assertTrue((output / "assets/js/site-core.js").is_file())
            self.assertTrue((output / "assets/js/i18n.js").is_file())
            self.assertTrue((output / "assets/js/form-validation.js").is_file())
            self.assertTrue((output / "assets/js/image-slots.js").is_file())
            self.assertTrue((output / "assets/js/complete-list.js").is_file())
            self.assertTrue((output / "assets/data/image-slots.json").is_file())
            self.assertTrue((output / "assets/img/favicon.svg").is_file())
            self.assertTrue((output / "assets/img/social-intelligence-modeling-overview.png").is_file())
            self.assertTrue((output / "assets/img/wechat-group-qr.jpg").is_file())
            self.assertEqual(data["stats"]["paper_count"], len(data["papers"]))
            self.assertEqual(stored["stats"]["paper_count"], len(stored["papers"]))
            self.assertGreater(data["stats"]["paper_count"], 300)
            self.assertEqual(complete["stats"]["paper_count"], len(complete["papers"]))
            self.assertGreater(complete["stats"]["paper_count"], data["stats"]["paper_count"])
            self.assertGreater(complete["stats"]["paper_count"], 900)
            self.assertEqual(
                data["stats"]["community_count"],
                sum(1 for paper in data["papers"] if paper["community_contribution"]),
            )
            self.assertGreaterEqual(data["stats"]["community_count"], 1)
            self.assertTrue(all(len(paper["abstract"]) <= build_site.ABSTRACT_EXCERPT_LIMIT for paper in data["papers"]))
            self.assertTrue(all("AI generated" not in paper["analogy_summary"] for paper in data["papers"]))
            self.assertTrue(all("翻译" not in paper["analogy_summary"] for paper in data["papers"]))
            self.assertTrue(all(isinstance(paper["community_contribution"], bool) for paper in complete["papers"]))
            self.assertTrue(
                all(bool(paper["contributor"]) == paper["community_contribution"] for paper in complete["papers"])
            )

    def test_internal_contributor_sentinel_is_not_exposed_as_community(self):
        data = build_site.build_site_data()
        self.assertFalse(any(paper["contributor"].casefold() == "me" for paper in data["papers"]))
        self.assertTrue(all(bool(paper["contributor"]) == paper["community_contribution"] for paper in data["papers"]))

    def test_only_explicit_community_prefix_is_public_provenance(self):
        self.assertEqual(build_site._community_contributor_label("community:@researcher"), "@researcher")
        self.assertEqual(build_site._community_contributor_label("@researcher"), "")
        self.assertEqual(build_site._community_contributor_label("me"), "")

    def test_analogy_summary_is_cleaned_and_bounded_before_export(self):
        source = "[AI generated] Short English summary. [翻译] 这部分不能显示" + ("x" * 400)
        cleaned = build_site._clean_analogy_summary(source)

        self.assertEqual(cleaned, "Short English summary.")
        self.assertNotIn("AI generated", cleaned)
        self.assertNotIn("翻译", cleaned)
        self.assertLessEqual(len(build_site._clean_analogy_summary("x" * 500)), build_site.ANALOGY_SUMMARY_LIMIT)

    def test_submission_ui_keeps_internal_import_fields_hidden(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")

        self.assertIn('data-zotero-dialog', html)
        self.assertIn('data-open-zotero', html)
        self.assertIn('data-generate-doi', html)
        self.assertIn('<input type="hidden" name="citation_key"', html)
        self.assertIn('<input type="hidden" name="title_translation"', html)
        self.assertIn('<input type="hidden" name="summary_citable_paragraph"', html)
        self.assertNotIn('data-stat="year_range"', html)
        self.assertNotIn('>Citation key<input', html)
        self.assertNotIn('>Translated title<input', html)
        self.assertNotIn('>Citable paragraph<textarea', html)
        optional_fields_index = html.index('<details class="optional-fields">')
        self.assertGreater(html.index('name="notes"'), optional_fields_index)
        self.assertIn('data-form-validation', html)
        self.assertIn('./assets/js/form-validation.js', html)

    def test_complete_list_progressively_renders_and_marks_explicit_community_submissions(self):
        html = (ROOT / "site/complete-list.html").read_text(encoding="utf-8")
        script = (ROOT / "site/assets/js/complete-list.js").read_text(encoding="utf-8")

        self.assertIn('data-complete-load-more', html)
        self.assertIn('./assets/css/complete-list.css', html)
        self.assertIn("const PAGE_SIZE = 80", script)
        self.assertIn("papers.slice(0, state.visibleLimit)", script)
        self.assertIn('badge.textContent = t("dynamic.community")', script)
        self.assertIn("paper.community_contribution", script)

    def test_optional_image_slots_are_configured_without_forcing_images_into_layout(self):
        config = json.loads((ROOT / "site/assets/data/image-slots.json").read_text(encoding="utf-8"))
        slots = config["slots"]
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        complete_html = (ROOT / "site/complete-list.html").read_text(encoding="utf-8")

        self.assertEqual(
            set(slots),
            {"hero_feature", "landscape_feature", "community_feature", "complete_list_feature"},
        )
        self.assertTrue(all(not slot["src"] for slot in slots.values()))
        self.assertIn('data-image-slot="hero_feature"', html)
        self.assertIn('data-image-slot="complete_list_feature"', complete_html)

    def test_language_switch_is_shared_across_both_site_pages(self):
        homepage = (ROOT / "site/index.html").read_text(encoding="utf-8")
        complete = (ROOT / "site/complete-list.html").read_text(encoding="utf-8")
        translations = (ROOT / "site/assets/js/i18n.js").read_text(encoding="utf-8")

        for html in (homepage, complete):
            self.assertIn('./assets/js/i18n.js', html)
            self.assertIn('data-language-toggle', html)
        self.assertIn('sim-site-language', translations)
        self.assertIn('sim:languagechange', translations)
        self.assertIn('"zh"', translations)

    def test_landscape_and_explorer_share_interactive_filters(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        script = (ROOT / "site/assets/js/app.js").read_text(encoding="utf-8")

        self.assertIn('class="chronology-map"', html)
        self.assertGreater(html.index('class="timeline-panel chronology-panel"'), html.index('class="landscape-layout"'))
        self.assertIn("function paperMatches", script)
        self.assertIn("function setExplorerFilters", script)
        self.assertIn("renderTaskBars(", script)
        self.assertIn('dot.className = "coordinate-dot"', script)
        self.assertIn('lane.className = "coordinate-lane"', script)
        self.assertIn("renderStageStats(state.data.papers, values.stage)", script)
        self.assertIn("renderTaskBars(state.data.papers, values.category)", script)
        self.assertIn("Date.UTC(2021, 0, 1)", script)
        self.assertIn('href="./complete-list.html"', html)

    def test_definition_and_community_follow_the_project_page_structure(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn('id="community"', html)
        self.assertIn('src="./assets/img/wechat-group-qr.jpg"', html)
        self.assertNotIn("/discussions", html)
        self.assertIn('href="#community"', html)
        self.assertGreater(html.index('id="community"'), html.index('id="paper-explorer"'))
        self.assertLess(html.index('id="community"'), html.index('id="contribute"'))
        self.assertIn("Under<wbr />standing", html)
        self.assertIn('class="back-to-top" href="#top"', html)
        self.assertIn('aria-label="Back to top"', html)
        self.assertNotIn('class="scope-boundary"', html)
        self.assertNotIn('class="definition-index"', html)
        self.assertNotIn("Community Discussions", readme)
        self.assertTrue((ROOT / "community/wechat-group-qr.jpg").is_file())

    def test_submission_no_longer_requires_or_displays_inclusion_rationale(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        script = (ROOT / "site/assets/js/app.js").read_text(encoding="utf-8")
        issue_form = (ROOT / ".github/ISSUE_TEMPLATE/paper_submission.yml").read_text(encoding="utf-8")

        self.assertNotIn("Why it belongs in this survey", html)
        self.assertNotIn("Why it belongs in this survey", script)
        self.assertNotIn("Why it belongs in this survey", issue_form)
        self.assertNotIn("rationale", issue_to_submission.REQUIRED_FIELDS)

    def test_submission_form_exposes_provenance_image_and_duplicate_guard(self):
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        script = (ROOT / "site/assets/js/app.js").read_text(encoding="utf-8")

        self.assertIn('name="contributor"', html)
        self.assertIn('name="pipeline_image_file"', html)
        self.assertIn("data-clear-submission", html)
        self.assertIn("recentlyOpenedSameSubmission", script)
        self.assertIn("submission.clearConfirm", script)
        self.assertIn('["Contributor", formData.get("contributor")', script)
        self.assertIn('"Pipeline image"', script)


class CommunityIssueIntakeTests(unittest.TestCase):
    def test_structured_issue_preserves_submitter_as_contributor(self):
        body = """<!-- sim-paper-submission:v1 -->
### Paper title
An Example Social Model

### DOI
https://doi.org/10.1234/example

### Paper URL
https://example.org/paper

### Project URL
https://github.com/example/project

### Authors
Ada Example, Lin Researcher

### Publication date
2026-08-27

### Venue
ExampleConf 2026

### Categories
Hate Speech Analysis | Meme and Multimodal Understanding

### Abstract
This paper models a social signal.

### Citation key
exampleSocialModel2026

### Analogy summary
A concise social-modeling analogy.

### Additional notes
Suggested for review.
"""
        submission = issue_to_submission.build_submission(
            body,
            submitter="outside-researcher",
            issue_number="42",
            issue_url="https://github.com/example/repo/issues/42",
        )
        paper = submission["papers"][0]

        self.assertEqual(paper["contributor"], "community:@outside-researcher")
        self.assertEqual(paper["doi"], "10.1234/example")
        self.assertEqual(paper["category"], ["Hate Speech Analysis", "Meme and Multimodal Understanding"])
        self.assertEqual(paper["citation_key"], "exampleSocialModel2026")
        self.assertEqual(paper["analogy_summary"], "A concise social-modeling analogy.")
        self.assertIn("GitHub issue #42", paper["notes"])
        self.assertTrue(paper["show_in_readme"])
        self.assertEqual(submission["meta"]["column_ids"], list(paper))
        self.assertEqual(paper["pipeline_image"], [])
        self.assertEqual(paper["invalid_fields"], [])

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "submit_template.json"
            path.write_text(json.dumps(submission), encoding="utf-8")
            errors = validate_submission.validate_json_structure(path, validate_submission.get_config_instance())
        self.assertEqual(errors, [])

    def test_visible_contributor_and_github_attachment_are_normalized(self):
        body = """### Paper title
Example
### DOI
10.1234/example-image
### Paper URL
https://example.org/paper
### Authors
Example Author
### Publication date
2026
### Categories
Hate Speech Analysis
### Abstract
Example abstract.
### Contributor
Research Group
### Pipeline image
![pipeline](https://github.com/user-attachments/assets/12345678-1234-1234-1234-123456789abc)
"""
        submission = issue_to_submission.build_submission(
            body,
            submitter="issue-author",
            issue_number="7",
            issue_url="https://github.com/example/repo/issues/7",
        )
        paper = submission["papers"][0]
        self.assertEqual(paper["contributor"], "community:Research Group")
        self.assertEqual(
            paper["pipeline_image"],
            ["https://github.com/user-attachments/assets/12345678-1234-1234-1234-123456789abc"],
        )

    def test_unknown_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown survey categories"):
            issue_to_submission._normalize_categories("Invented Social Task")

    def test_non_main_submission_marker_is_idempotent_for_json_and_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            json_path = root / "submit_template.json"
            json_path.write_text(
                json.dumps({"papers": [{"contributor": "Research Lab"}, {"contributor": "community:@person"}]}),
                encoding="utf-8",
            )
            self.assertEqual(mark_community_submission.mark_json(json_path, "pr-author"), 1)
            marked_json = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(marked_json["papers"][0]["contributor"], "community:Research Lab")
            self.assertEqual(marked_json["papers"][1]["contributor"], "community:@person")

            csv_path = root / "submit_template.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows([["title", "contributor"], ["title", "contributor"], ["Paper", ""]])
            self.assertEqual(mark_community_submission.mark_csv(csv_path, "pr-author"), 1)
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[2][1], "community:@pr-author")

    def test_issue_image_downloader_restricts_hosts_and_detects_image_magic(self):
        self.assertTrue(
            download_issue_images.allowed_url(
                "https://github.com/user-attachments/assets/12345678-1234-1234-1234-123456789abc"
            )
        )
        self.assertFalse(download_issue_images.allowed_url("https://example.com/pipeline.png"))
        self.assertEqual(download_issue_images.image_extension(b"\x89PNG\r\n\x1a\nrest"), ".png")

    def test_issue_image_downloader_materializes_a_project_relative_asset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            submission_path = root / "submit_template.json"
            submission_path.write_text(
                json.dumps(
                    {
                        "papers": [
                            {
                                "uid": "abc12345",
                                "pipeline_image": [
                                    "https://github.com/user-attachments/assets/12345678-1234-1234-1234-123456789abc"
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            png = b"\x89PNG\r\n\x1a\nexample"
            with patch.object(download_issue_images, "download", return_value=png):
                created = download_issue_images.materialize_images(submission_path, root)

            stored = json.loads(submission_path.read_text(encoding="utf-8"))
            reference = stored["papers"][0]["pipeline_image"][0]
            self.assertTrue(reference.startswith("engineering/assets/abc12345/community-pipeline-"))
            self.assertEqual(created, [root / reference])
            self.assertEqual((root / reference).read_bytes(), png)


class NotificationTests(unittest.TestCase):
    def test_failure_subject_prefix_is_unmistakable(self):
        prefix, heading, accent, outcome = send_notification._status_details("failure")
        self.assertIn("FAILED", prefix)
        self.assertIn("failed", heading.casefold())
        self.assertEqual(accent, "#b42318")
        self.assertIn("not published", outcome.casefold())


class ContributorProvenanceTests(unittest.TestCase):
    def test_readme_distinguishes_external_but_not_team_contributors(self):
        generator = ReadmeGenerator()
        external = generator._generate_title_authors_cell(
            Paper(title="Community Paper", authors="Alice", contributor="community:@outside-researcher")
        )
        unmarked_external_value = generator._generate_title_authors_cell(
            Paper(title="Imported Paper", authors="Alice", contributor="@outside-researcher")
        )
        internal = generator._generate_title_authors_cell(
            Paper(title="Team Paper", authors="Alice", contributor="me")
        )

        self.assertIn("Community-Contribution", external)
        self.assertIn("Community contribution by @outside-researcher", external)
        self.assertNotIn("Community-Contribution", unmarked_external_value)
        self.assertNotIn("Community-Contribution", internal)


class StableDatabaseInsertionTests(unittest.TestCase):
    def test_new_paper_is_inserted_without_reordering_existing_papers(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        existing_first = Paper(uid="first", doi="10.1000/first", title="First", category="Category B")
        existing_second = Paper(uid="second", doi="10.1000/second", title="Second", category="Category A")
        existing_third = Paper(uid="third", doi="10.1000/third", title="Third", category="Category B")
        incoming = Paper(uid="incoming", doi="10.1000/incoming", title="Incoming", category="Category A")

        manager.config = MagicMock()
        manager.config.get_active_categories.return_value = [
            {"unique_name": "Category A", "order": 1},
            {"unique_name": "Category B", "order": 2},
        ]
        manager.update_utils = MagicMock()
        manager.update_utils.repair_related_paper_references.return_value = 0
        manager.load_database = MagicMock(
            return_value=(True, [existing_first, existing_second, existing_third])
        )
        manager.save_database = MagicMock(return_value=True)

        with patch.object(Paper, "validate_paper_fields", return_value=(True, [], [])):
            added, conflicts, _ = manager.add_papers([incoming], "mark")

        self.assertEqual(added, [incoming])
        self.assertEqual(conflicts, [])
        saved = manager.save_database.call_args.args[0]
        self.assertEqual([paper.uid for paper in saved], ["first", "incoming", "second", "third"])
        self.assertEqual(
            [paper.uid for paper in saved if paper.uid != "incoming"],
            ["first", "second", "third"],
        )


class AutomationWiringTests(unittest.TestCase):
    def test_repository_automation_treats_paper_file_as_metadata_only(self):
        processing = (ROOT / ".github/workflows/process_submission.yml").read_text(encoding="utf-8")
        paper = Paper(
            uid="metadata-only",
            title="Metadata-only paper",
            paper_file="engineering/assets/metadata-only/local-paper.pdf",
        )

        with patch.dict(validate_submission.os.environ, {"IGNORE_PAPER_FILE_ASSETS": "true"}):
            errors = validate_submission.validate_paper_assets(
                paper,
                config=validate_submission.get_config_instance(),
            )

        self.assertEqual(errors, [])
        self.assertIn('IGNORE_PAPER_FILE_ASSETS: "true"', processing)
        self.assertNotIn("temporary_submission_pdfs.py", processing)
        self.assertIn('[[ "${source_file,,}" == *.pdf ]]', processing)

    def test_accepted_update_triggers_pages_and_failure_mail_is_visible(self):
        processing = (ROOT / ".github/workflows/process_submission.yml").read_text(encoding="utf-8")
        deployment = (ROOT / ".github/workflows/deploy_pages.yml").read_text(encoding="utf-8")
        intake = (ROOT / ".github/workflows/intake_paper_issue.yml").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        self.assertIn('git commit -m "Process paper submission from @$PR_USER"', processing)
        self.assertNotIn('git commit -m "[skip ci]', processing)
        self.assertIn("workflow_call:", processing)
        self.assertIn("uses: ./.github/workflows/process_submission.yml", intake)
        self.assertIn("submission_head_sha:", intake)
        self.assertNotIn('gh pr edit "$pr_url" --add-label "Action: Process"', intake)
        self.assertIn("engineering/paper_database_for_survey.csv", deployment)
        self.assertIn("engineering/paper_database_complete_list.csv", deployment)
        self.assertIn("complete-list-data.json", deployment)
        self.assertIn("lfs: true", deployment)
        self.assertIn("actions/upload-pages-artifact@v5", deployment)
        self.assertIn("actions/deploy-pages@v4", deployment)
        self.assertIn("notify-intake-failure:", intake)
        self.assertIn("send_notification.py", intake)
        self.assertIn("🚨 [SIM AUTO UPDATE FAILED]", contributing)


if __name__ == "__main__":
    unittest.main()
