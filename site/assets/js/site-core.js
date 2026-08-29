(() => {
  "use strict";

  const normalize = (value) =>
    String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase();

  const isSafeUrl = (value) => {
    try {
      const parsed = new URL(value, window.location.href);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch (_error) {
      return false;
    }
  };

  const isSafeImageUrl = (value) => {
    const source = String(value || "").trim();
    if (!source) return false;
    if (/^(?:\.\/)?assets\/img\/[A-Za-z0-9._/-]+$/.test(source)) return true;
    return isSafeUrl(source);
  };

  const isArxivIdentifier = (value) => {
    const source = String(value || "").trim();
    if (!source) return false;
    return (
      /^(?:https?:\/\/(?:dx\.)?doi\.org\/)?10\.48550\/arxiv\.\d{4}\.\d{4,5}(?:v\d+)?(?:[?#].*)?$/i.test(source) ||
      /^arxiv:\s*\d{4}\.\d{4,5}(?:v\d+)?$/i.test(source) ||
      /^https?:\/\/(?:www\.)?arxiv\.org\/(?:abs|pdf)\/\d{4}\.\d{4,5}(?:v\d+)?(?:\.pdf)?(?:[?#].*)?$/i.test(source)
    );
  };

  const paperVenue = (paper) => {
    const recordedVenue = String(paper?.conference || "").trim();
    if (recordedVenue) return recordedVenue;
    return isArxivIdentifier(paper?.doi) ? "arXiv" : "";
  };

  const formatDate = (value, fallback = "Unknown build time", locale = "en") => {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    }).format(date);
  };

  const setupNavigation = ({ header, navToggle, nav } = {}) => {
    const resolvedHeader = header || document.querySelector("[data-header]");
    const resolvedToggle = navToggle || document.querySelector(".nav-toggle");
    const resolvedNav = nav || document.querySelector(".primary-nav");
    const close = () => {
      resolvedNav?.classList.remove("is-open");
      resolvedToggle?.setAttribute("aria-expanded", "false");
      document.body.classList.remove("nav-open");
    };
    const updateHeader = () => resolvedHeader?.classList.toggle("is-scrolled", window.scrollY > 18);
    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
    resolvedToggle?.addEventListener("click", () => {
      const open = resolvedToggle.getAttribute("aria-expanded") !== "true";
      resolvedToggle.setAttribute("aria-expanded", String(open));
      resolvedNav?.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
    });
    resolvedNav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", close));
    return { close };
  };

  window.SIMSite = Object.freeze({
    formatDate,
    isSafeImageUrl,
    isSafeUrl,
    isArxivIdentifier,
    normalize,
    paperVenue,
    setupNavigation,
  });
})();
