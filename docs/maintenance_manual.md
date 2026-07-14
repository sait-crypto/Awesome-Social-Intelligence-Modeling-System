[Document Homepage](./../README.md)

# Complete List maintenance

The compact paper index is maintained separately from the curated review table:

- Source database: `paper_database_complete_list.csv`
- Generated output: `COMPLETE_LIST.md`
- Configuration: `complete_list_database` and `complete_list_output` in `[paths]`
- Generator: `python src/convert.py`

The source uses the same two-header-row `Paper` CSV schema as the core database. It is read directly by `ReadmeGenerator` and never enters `AIGenerator`.

`COMPLETE_LIST.md` is overwritten whenever the normal README generator runs. Edit the database rather than the generated Markdown. The compact output includes only title, venue, and Paper/Project/DOI links. Every titled database row is retained, including entries with `show_in_readme=false` and conflict variants; only rows without a title are omitted.

During the normal submission update, each validated input entry is deep-copied into `paper_database_complete_list.csv` before any optional AI generation. The existing AI stage then processes only the copy continuing toward the core database. The Complete List database therefore receives the submitted fields exactly as they existed before automatic AI completion.

The automatic AI scope for this update stage is controlled by `update_generation_scope` in the `[ai]` section of `config/config.ini`. Use `all` for the original missing-field completion behavior, or `analogy_only` to generate only a missing `analogy_summary`. The latter never generates summary fields and never overwrites an existing analogy. This setting does not restrict manual field generation in the GUI.

Maintainers can use the submit GUI's **完整库** button to load and edit `paper_database_complete_list.csv` directly. Saving the loaded file updates that database without involving AI; run `python src/convert.py` afterward to regenerate the Markdown list.

For pasted Zotero metadata, `import_notes_from_meta` in the `[zotero]` section controls whether nested `"note"` content is copied into `Paper.notes`. Set it to `false` to ignore Zotero notes for both “new from Zotero” and “fill current form”; existing form notes are not cleared.

# Paper metadata

Edit only `config/paper_metadata.json` to update the paper introduction, arXiv badge, and BibTeX. Set `arxiv_id` to the identifier only (for example, `2601.01234`); `paper_url` remains the badge and paper-title destination. Running `python src/convert.py` rewrites the managed badge row, introduction, and both Citation sections in `README.md` from that file. Do not remove the `PAPER_*_START` / `PAPER_*_END` comments: generation fails without writing the README if any managed block is missing.

README long-field limits are configured independently in `config/config.ini` under `[readme]`: `max_analogy_summary_length`, `max_summary_motivation_length`, `max_summary_innovation_length`, `max_summary_method_length`, `max_summary_conclusion_length`, `max_summary_limitation_length`, and `max_notes_length`. Values are character counts; use `0` to disable truncation for a field. Multi-category papers are rendered fully once, with later category appearances kept as one-row links to the full entry.

# Category changes

Rename, merge, or remove categories through `CATEGORIES_CHANGE_LIST` in `config/categories_config.py`. Each old category must map to an enabled target before its category definition is removed. README generation normalizes legacy database values in memory, so existing database rows remain compatible without a bulk rewrite. Run `python config/categories_config.py` and the test suite after changing the taxonomy.
