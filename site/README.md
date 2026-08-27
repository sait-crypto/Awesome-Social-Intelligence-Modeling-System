# Website source

The GitHub Pages build copies this directory and injects generated paper data. Keep source files organized by responsibility:

- `index.html`: survey homepage structure.
- `complete-list.html`: compact repository-wide paper index.
- `assets/css/styles.css`: shared layout and homepage presentation.
- `assets/css/forms.css`: submission validation states.
- `assets/css/complete-list.css`: complete-list page presentation.
- `assets/css/image-slots.css`: optional configured figures.
- `assets/js/site-core.js`: shared URL, text, date, and navigation helpers.
- `assets/js/i18n.js`: English/Chinese interface translations and persisted language selection.
- `assets/js/app.js`: homepage data exploration and submission orchestration.
- `assets/js/form-validation.js`: browser-side submission preflight.
- `assets/js/complete-list.js`: progressive complete-list rendering.
- `assets/js/image-slots.js`: optional image-slot loader.
- `assets/data/image-slots.json`: image-slot configuration.

## Optional image slots

The source includes `hero_feature`, `landscape_feature`, `community_feature`, and `complete_list_feature`. They remain hidden while `src` is empty. To enable one, copy an image into `assets/img/`, then set its relative `src`, accessible `alt`, and optional `caption` in `assets/data/image-slots.json`.

Generated files under `site-dist/` are disposable and must not be edited or committed.
