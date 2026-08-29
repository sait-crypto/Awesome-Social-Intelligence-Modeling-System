(() => {
  "use strict";

  const endpoint = document
    .querySelector('meta[name="sim-upload-endpoint"]')
    ?.content.trim()
    .replace(/\/+$/, "") || "";
  const FILE_PROGRESS_TIMEOUT_MS = 45_000;

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

  const buildUploadResult = (submissionId, uploadedItems) => {
    const items = [...uploadedItems].sort((left, right) => {
      if (left.kind !== right.kind) return left.kind === "pipeline" ? -1 : 1;
      return Number(left.index) - Number(right.index);
    });
    return {
      submissionId,
      uploadedItems: items.map(({ kind, index, reference }) => ({ kind, index, reference })),
      pipelineReferences: items
        .filter((item) => item.kind === "pipeline")
        .map((item) => item.reference),
      paperReference: items.find((item) => item.kind === "paper")?.reference || "",
    };
  };

  async function uploadFile(file, { submissionId, kind, index, signal, timeoutMs = FILE_PROGRESS_TIMEOUT_MS }) {
    const controller = new AbortController();
    let timedOut = false;
    const abortFromCaller = () => controller.abort();
    if (signal?.aborted) controller.abort();
    else signal?.addEventListener("abort", abortFromCaller, { once: true });
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    let response;
    let result = null;
    try {
      response = await fetch(`${endpoint}/v1/files`, {
        method: "POST",
        mode: "cors",
        credentials: "omit",
        signal: controller.signal,
        headers: {
          "Content-Type": file.type || "application/octet-stream",
          "X-SIM-Submission": submissionId,
          "X-SIM-File-Kind": kind,
          "X-SIM-File-Index": String(index),
          "X-SIM-File-Name": encodeURIComponent(file.name || `${kind}-${index}`),
        },
        body: file,
      });
      try {
        result = await response.json();
      } catch (error) {
        if (timedOut) throw error;
        // The status code remains useful when the service did not return JSON.
      }
      if (!response.ok || !result?.reference) {
        throw new Error(result?.error || `Upload failed (${response.status || "network error"}).`);
      }
      return result;
    } catch (error) {
      if (timedOut) {
        const timeoutError = new Error(`Upload timed out after ${Math.round(timeoutMs / 1000)} seconds.`);
        timeoutError.name = "TimeoutError";
        throw timeoutError;
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
      signal?.removeEventListener("abort", abortFromCaller);
    }
  }

  async function uploadSubmissionFiles({
    pipelineFiles = [],
    paperFile = null,
    onProgress,
    resumeState = null,
    signal,
    timeoutMs,
  } = {}) {
    if (!isConfigured()) throw new Error("Direct upload is not configured.");
    const jobs = [
      ...pipelineFiles.map((file, index) => ({ file, kind: "pipeline", index })),
      ...(paperFile instanceof File && paperFile.size ? [{ file: paperFile, kind: "paper", index: 0 }] : []),
    ];
    const submissionId = String(resumeState?.submissionId || randomSubmissionId());
    const uploaded = Array.isArray(resumeState?.uploadedItems)
      ? resumeState.uploadedItems.map((item) => ({ ...item }))
      : [];
    const startIndex = Math.max(0, Math.min(jobs.length, Number(resumeState?.nextJobIndex) || 0));
    for (let index = startIndex; index < jobs.length; index += 1) {
      onProgress?.({ completed: uploaded.length, total: jobs.length, file: jobs[index].file });
      try {
        const result = await uploadFile(jobs[index].file, {
          ...jobs[index],
          submissionId,
          signal,
          timeoutMs,
        });
        uploaded.push({ ...result, kind: jobs[index].kind, index: jobs[index].index });
      } catch (error) {
        const uploadError = error instanceof Error ? error : new Error(String(error));
        uploadError.uploadState = {
          submissionId,
          uploadedItems: uploaded.map((item) => ({ ...item })),
          nextJobIndex: index,
          pendingFileName: jobs[index].file.name,
          total: jobs.length,
        };
        uploadError.partialResult = buildUploadResult(submissionId, uploaded);
        throw uploadError;
      }
    }
    onProgress?.({ completed: uploaded.length, total: jobs.length, file: null });
    return buildUploadResult(submissionId, uploaded);
  }

  window.SIMUpload = {
    fileTimeoutSeconds: Math.round(FILE_PROGRESS_TIMEOUT_MS / 1000),
    isConfigured,
    uploadSubmissionFiles,
  };
})();
