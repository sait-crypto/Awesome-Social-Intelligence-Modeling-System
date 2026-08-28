(() => {
  "use strict";

  const endpoint = document
    .querySelector('meta[name="sim-upload-endpoint"]')
    ?.content.trim()
    .replace(/\/+$/, "") || "";

  const isConfigured = () => {
    try {
      return new URL(endpoint).protocol === "https:";
    } catch (_error) {
      return false;
    }
  };

  const randomSubmissionId = () => {
    if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
  };

  async function uploadFile(file, { submissionId, kind, index, signal }) {
    const response = await fetch(`${endpoint}/v1/files`, {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      signal,
      headers: {
        "Content-Type": file.type || "application/octet-stream",
        "X-SIM-Submission": submissionId,
        "X-SIM-File-Kind": kind,
        "X-SIM-File-Index": String(index),
        "X-SIM-File-Name": encodeURIComponent(file.name || `${kind}-${index}`),
      },
      body: file,
    });
    let result = null;
    try {
      result = await response.json();
    } catch (_error) {
      // The status code remains the useful error when the service did not return JSON.
    }
    if (!response.ok || !result?.reference) {
      throw new Error(result?.error || `Upload failed (${response.status || "network error"}).`);
    }
    return result;
  }

  async function uploadSubmissionFiles({ pipelineFiles = [], paperFile = null, onProgress, signal } = {}) {
    if (!isConfigured()) throw new Error("Direct upload is not configured.");
    const submissionId = randomSubmissionId();
    const jobs = [
      ...pipelineFiles.map((file, index) => ({ file, kind: "pipeline", index })),
      ...(paperFile instanceof File && paperFile.size ? [{ file: paperFile, kind: "paper", index: 0 }] : []),
    ];
    const uploaded = [];
    for (let index = 0; index < jobs.length; index += 1) {
      onProgress?.({ completed: index, total: jobs.length, file: jobs[index].file });
      uploaded.push(await uploadFile(jobs[index].file, { ...jobs[index], submissionId, signal }));
    }
    onProgress?.({ completed: jobs.length, total: jobs.length, file: null });
    return {
      submissionId,
      pipelineReferences: uploaded
        .filter((item) => item.kind === "pipeline")
        .map((item) => item.reference),
      paperReference: uploaded.find((item) => item.kind === "paper")?.reference || "",
    };
  }

  window.SIMUpload = { isConfigured, uploadSubmissionFiles };
})();
