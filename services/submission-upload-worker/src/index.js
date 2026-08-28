const IMAGE_LIMIT = 10 * 1024 * 1024;
const PDF_LIMIT = 50 * 1024 * 1024;
const CHUNK_BYTES = 8 * 1024 * 1024;
const DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60;
const MAX_TTL_SECONDS = 14 * 24 * 60 * 60;

const encoder = new TextEncoder();

function json(data, status = 200, origin = "") {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...(origin ? corsHeaders(origin) : {}),
    },
  });
}

function allowedOrigin(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((value) => value.trim().replace(/\/+$/, ""))
    .filter(Boolean);
  return allowed.includes(origin.replace(/\/+$/, "")) ? origin : "";
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": [
      "Content-Type",
      "X-SIM-Submission",
      "X-SIM-File-Kind",
      "X-SIM-File-Index",
      "X-SIM-File-Name",
    ].join(", "),
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function base64Url(bytes) {
  let binary = "";
  for (const byte of new Uint8Array(bytes)) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function signature(secret, key, expires) {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return base64Url(await crypto.subtle.sign("HMAC", cryptoKey, encoder.encode(`${key}|${expires}`)));
}

function safeEqual(left, right) {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function imageExtension(bytes) {
  const data = new Uint8Array(bytes);
  if (data.length >= 8 && [137, 80, 78, 71, 13, 10, 26, 10].every((value, index) => data[index] === value)) return ".png";
  if (data.length >= 3 && data[0] === 255 && data[1] === 216 && data[2] === 255) return ".jpg";
  const head6 = new TextDecoder().decode(data.slice(0, 6));
  if (head6 === "GIF87a" || head6 === "GIF89a") return ".gif";
  const head4 = new TextDecoder().decode(data.slice(0, 4));
  const webp = new TextDecoder().decode(data.slice(8, 12));
  if (head4 === "RIFF" && webp === "WEBP") return ".webp";
  return "";
}

function validateUpload(bytes, kind) {
  if (kind === "pipeline") {
    const extension = imageExtension(bytes);
    if (!extension) throw new Error("Pipeline files must be PNG, JPEG, GIF, or WebP images.");
    return { extension, contentType: extension === ".jpg" ? "image/jpeg" : `image/${extension.slice(1)}` };
  }
  const header = new TextDecoder().decode(new Uint8Array(bytes).slice(0, 5));
  if (header !== "%PDF-") throw new Error("The paper file must be a valid PDF container.");
  return { extension: ".pdf", contentType: "application/pdf" };
}

function cleanFilename(value, fallback) {
  let decoded = "";
  try {
    decoded = decodeURIComponent(value || "");
  } catch (_error) {
    decoded = "";
  }
  return decoded.replace(/[\u0000-\u001f\u007f]/g, "").replace(/[\\/]/g, "-").trim().slice(0, 180) || fallback;
}

async function upload(request, env, origin) {
  if (!origin) return json({ error: "This website origin is not allowed." }, 403);
  if (!env.SUBMISSION_FILES || String(env.DOWNLOAD_SIGNING_SECRET || "").length < 32) {
    return json({ error: "The upload service is not fully configured." }, 503, origin);
  }
  if (env.UPLOAD_RATE_LIMITER) {
    const actor = request.headers.get("CF-Connecting-IP") || origin;
    const { success } = await env.UPLOAD_RATE_LIMITER.limit({ key: `upload:${actor}` });
    if (!success) return json({ error: "Too many uploads. Please wait one minute and try again." }, 429, origin);
  }

  const submissionId = request.headers.get("X-SIM-Submission") || "";
  const kind = request.headers.get("X-SIM-File-Kind") || "";
  const index = Number(request.headers.get("X-SIM-File-Index"));
  if (!/^(?:[a-f0-9]{32}|[a-f0-9-]{36})$/i.test(submissionId)) {
    return json({ error: "Invalid submission identifier." }, 400, origin);
  }
  if (!new Set(["pipeline", "paper"]).has(kind) || !Number.isInteger(index) || index < 0) {
    return json({ error: "Invalid file slot." }, 400, origin);
  }
  if ((kind === "pipeline" && index > 3) || (kind === "paper" && index !== 0)) {
    return json({ error: "The submission contains too many files." }, 400, origin);
  }

  const declaredSize = Number(request.headers.get("Content-Length") || 0);
  const limit = kind === "paper" ? PDF_LIMIT : IMAGE_LIMIT;
  if (declaredSize > limit) return json({ error: "The selected file exceeds its size limit." }, 413, origin);
  const bytes = await request.arrayBuffer();
  if (!bytes.byteLength || bytes.byteLength > limit) {
    return json({ error: "The selected file is empty or exceeds its size limit." }, 413, origin);
  }

  let detected;
  try {
    detected = validateUpload(bytes, kind);
  } catch (error) {
    return json({ error: error.message }, 415, origin);
  }

  const key = `${submissionId}/${kind}-${index}${detected.extension}`;
  const ttl = Math.min(Math.max(Number(env.FILE_TTL_SECONDS) || DEFAULT_TTL_SECONDS, 3600), MAX_TTL_SECONDS);
  const expires = Math.floor(Date.now() / 1000) + ttl;
  const filename = cleanFilename(request.headers.get("X-SIM-File-Name"), `${kind}${detected.extension}`);
  const chunks = Math.ceil(bytes.byteLength / CHUNK_BYTES);
  for (let chunkIndex = 0; chunkIndex < chunks; chunkIndex += 1) {
    const start = chunkIndex * CHUNK_BYTES;
    await env.SUBMISSION_FILES.put(
      `${key}:chunk:${chunkIndex}`,
      bytes.slice(start, Math.min(start + CHUNK_BYTES, bytes.byteLength)),
      { expirationTtl: ttl },
    );
  }
  await env.SUBMISSION_FILES.put(
    `${key}:meta`,
    JSON.stringify({ expires, filename, kind, contentType: detected.contentType, size: bytes.byteLength, chunks }),
    { expirationTtl: ttl },
  );

  const signed = await signature(env.DOWNLOAD_SIGNING_SECRET, key, expires);
  const path = key.split("/").map(encodeURIComponent).join("/");
  const reference = `${new URL(request.url).origin}/v1/files/${path}?expires=${expires}&signature=${signed}`;
  return json({ reference, submissionId, kind, index, name: filename, size: bytes.byteLength, expires }, 201, origin);
}

async function download(request, env, key) {
  if (!env.SUBMISSION_FILES || String(env.DOWNLOAD_SIGNING_SECRET || "").length < 32 || !key || key.includes("..")) {
    return new Response("Not found", { status: 404 });
  }
  const url = new URL(request.url);
  const expires = Number(url.searchParams.get("expires"));
  const supplied = url.searchParams.get("signature") || "";
  if (!Number.isInteger(expires) || expires < Math.floor(Date.now() / 1000)) return new Response("Link expired", { status: 410 });
  const expected = await signature(env.DOWNLOAD_SIGNING_SECRET, key, expires);
  if (!safeEqual(supplied, expected)) return new Response("Forbidden", { status: 403 });

  const rawMetadata = await env.SUBMISSION_FILES.get(`${key}:meta`);
  if (!rawMetadata) return new Response("Not found", { status: 404 });
  let metadata;
  try {
    metadata = JSON.parse(rawMetadata);
  } catch (_error) {
    return new Response("Stored metadata is invalid", { status: 500 });
  }
  if (Number(metadata.expires) < Math.floor(Date.now() / 1000)) return new Response("Link expired", { status: 410 });
  const storedSize = Number(metadata.size);
  if (
    !Number.isInteger(metadata.chunks)
    || metadata.chunks < 1
    || metadata.chunks > 7
    || !Number.isInteger(storedSize)
    || storedSize < 1
    || storedSize > PDF_LIMIT
  ) {
    return new Response("Stored metadata is invalid", { status: 500 });
  }
  let chunkIndex = 0;
  let delivered = 0;
  const content = new ReadableStream({
    async pull(controller) {
      if (chunkIndex >= metadata.chunks) {
        if (delivered !== storedSize) controller.error(new Error("Stored file is incomplete"));
        else controller.close();
        return;
      }
      const part = await env.SUBMISSION_FILES.get(`${key}:chunk:${chunkIndex}`, "arrayBuffer");
      if (!(part instanceof ArrayBuffer)) {
        controller.error(new Error("Stored file is incomplete"));
        return;
      }
      const bytes = new Uint8Array(part);
      if (delivered + bytes.byteLength > storedSize) {
        controller.error(new Error("Stored metadata is invalid"));
        return;
      }
      delivered += bytes.byteLength;
      chunkIndex += 1;
      controller.enqueue(bytes);
      if (chunkIndex >= metadata.chunks) {
        if (delivered !== storedSize) controller.error(new Error("Stored file is incomplete"));
        else controller.close();
      }
    },
  });

  const extension = key.slice(key.lastIndexOf("."));
  const asciiFilename = metadata.kind === "paper" ? "submitted-paper.pdf" : `pipeline${extension}`;
  return new Response(content, {
    headers: {
      "Content-Type": metadata.contentType,
      "Content-Length": String(storedSize),
      "Content-Disposition": `attachment; filename="${asciiFilename}"; filename*=UTF-8''${encodeURIComponent(metadata.filename)}`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = allowedOrigin(request, env);
    if (request.method === "OPTIONS") {
      return origin ? new Response(null, { status: 204, headers: corsHeaders(origin) }) : new Response(null, { status: 403 });
    }
    if (request.method === "GET" && url.pathname === "/health") return json({ ok: true, storage: "kv" });
    if (request.method === "POST" && url.pathname === "/v1/files") return upload(request, env, origin);
    if (request.method === "GET" && url.pathname.startsWith("/v1/files/")) {
      const key = url.pathname.slice("/v1/files/".length).split("/").map(decodeURIComponent).join("/");
      return download(request, env, key);
    }
    return new Response("Not found", { status: 404 });
  },
};
