import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.js";

class MemoryKV {
  constructor() {
    this.objects = new Map();
  }

  async put(key, value) {
    this.objects.set(
      key,
      typeof value === "string" ? value : new Uint8Array(value),
    );
  }

  async get(key, type) {
    const stored = this.objects.get(key);
    if (!stored) return null;
    if (type === "arrayBuffer") {
      const bytes = typeof stored === "string" ? new TextEncoder().encode(stored) : stored;
      return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    }
    return typeof stored === "string" ? stored : new TextDecoder().decode(stored);
  }
}

const env = () => ({
  SUBMISSION_FILES: new MemoryKV(),
  DOWNLOAD_SIGNING_SECRET: "a-test-secret-that-is-definitely-long-enough",
  ALLOWED_ORIGINS: "https://sait-crypto.github.io",
  FILE_TTL_SECONDS: "3600",
});

test("chunks and reconstructs a PDF larger than one KV value chunk", async () => {
  const bindings = env();
  const pdf = new Uint8Array(8 * 1024 * 1024 + 17);
  pdf.set(new TextEncoder().encode("%PDF-1.7"));
  const response = await worker.fetch(
    new Request("https://upload.example/v1/files", {
      method: "POST",
      headers: {
        Origin: "https://sait-crypto.github.io",
        "Content-Type": "application/pdf",
        "X-SIM-Submission": "12345678-1234-1234-1234-123456789abc",
        "X-SIM-File-Kind": "paper",
        "X-SIM-File-Index": "0",
        "X-SIM-File-Name": "paper.pdf",
      },
      body: pdf,
    }),
    bindings,
  );
  assert.equal(response.status, 201);
  assert.equal(bindings.SUBMISSION_FILES.objects.size, 3);
  const result = await response.json();
  const downloaded = await worker.fetch(new Request(result.reference), bindings);
  assert.equal(downloaded.status, 200);
  assert.deepEqual(new Uint8Array(await downloaded.arrayBuffer()), pdf);
});

test("uploads a validated image and serves it through the signed reference", async () => {
  const bindings = env();
  const png = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3]);
  const response = await worker.fetch(
    new Request("https://upload.example/v1/files", {
      method: "POST",
      headers: {
        Origin: "https://sait-crypto.github.io",
        "Content-Type": "image/png",
        "X-SIM-Submission": "12345678-1234-1234-1234-123456789abc",
        "X-SIM-File-Kind": "pipeline",
        "X-SIM-File-Index": "0",
        "X-SIM-File-Name": encodeURIComponent("pipeline.png"),
      },
      body: png,
    }),
    bindings,
  );
  assert.equal(response.status, 201);
  const result = await response.json();
  assert.match(result.reference, /expires=\d+&signature=/);

  const downloaded = await worker.fetch(new Request(result.reference), bindings);
  assert.equal(downloaded.status, 200);
  assert.equal(downloaded.headers.get("Content-Type"), "image/png");
  assert.deepEqual(new Uint8Array(await downloaded.arrayBuffer()), png);
});

test("rejects an unapproved origin and a forged file type", async () => {
  const bindings = env();
  const headers = {
    Origin: "https://sait-crypto.github.io",
    "Content-Type": "image/png",
    "X-SIM-Submission": "12345678-1234-1234-1234-123456789abc",
    "X-SIM-File-Kind": "pipeline",
    "X-SIM-File-Index": "0",
    "X-SIM-File-Name": "fake.png",
  };
  const badOrigin = await worker.fetch(
    new Request("https://upload.example/v1/files", {
      method: "POST",
      headers: { ...headers, Origin: "https://attacker.example" },
      body: new Uint8Array([1]),
    }),
    bindings,
  );
  assert.equal(badOrigin.status, 403);

  const fake = await worker.fetch(
    new Request("https://upload.example/v1/files", {
      method: "POST",
      headers,
      body: new TextEncoder().encode("not an image"),
    }),
    bindings,
  );
  assert.equal(fake.status, 415);
  assert.equal(bindings.SUBMISSION_FILES.objects.size, 0);
});
