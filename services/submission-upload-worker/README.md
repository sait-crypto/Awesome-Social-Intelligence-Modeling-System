# Temporary submission upload service

This optional Cloudflare Worker removes the manual attachment step from the static GitHub Pages form. It accepts at most four pipeline images (10 MiB each) and one paper PDF (50 MiB), checks the file signatures, splits large PDFs into bounded Workers KV values, and returns seven-day signed download URLs. KV expiry removes every chunk automatically.

## Deploy once

1. Create the private KV namespace and copy its generated ID into `wrangler.toml`; adjust `ALLOWED_ORIGINS` if needed:

   ```console
   npx wrangler kv namespace create SUBMISSION_FILES
   ```

2. Create a long random signing secret:

   ```console
   npx wrangler secret put DOWNLOAD_SIGNING_SECRET
   ```

3. Deploy:

   ```console
   npx wrangler deploy
   ```

4. In the GitHub repository, create the Actions variable `SIM_UPLOAD_ENDPOINT` with the deployed Worker origin, for example `https://sim-paper-submission-upload.example.workers.dev`. Re-run the Pages deployment.

No Cloudflare credential or signing secret is placed in the static website. The Worker includes a 20-request-per-minute upload limiter, and KV expiration removes abandoned uploads without a cleanup workflow.

The signed references appear in a public GitHub issue until they expire. This matches the visibility of GitHub issue attachments; submitters should upload only the paper and figures intended for review.
