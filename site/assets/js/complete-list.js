(() => {
  "use strict";

  const { formatDate, isSafeUrl, normalize, setupNavigation } = window.SIMSite;
  const i18n = window.SIMI18n;
  const t = (key, values) => i18n.t(key, values);
  const locale = () => (i18n.getLanguage() === "zh" ? "zh-CN" : "en");
  const PAGE_SIZE = 80;
  const elements = {
    header: document.querySelector("[data-header]"),
    navToggle: document.querySelector(".nav-toggle"),
    nav: document.querySelector(".primary-nav"),
    search: document.querySelector("[data-complete-search]"),
    sort: document.querySelector("[data-complete-sort]"),
    count: document.querySelector("[data-complete-count]"),
    total: document.querySelector("[data-complete-total]"),
    list: document.querySelector("[data-complete-list]"),
    generated: document.querySelector("[data-complete-generated]"),
    loadMore: document.querySelector("[data-complete-load-more]"),
  };

  const state = { data: null, visibleLimit: PAGE_SIZE };

  const appendLink = (container, label, url) => {
    if (!isSafeUrl(url)) return;
    if (container.childElementCount) container.append(document.createTextNode(" · "));
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = label;
    container.append(link);
  };

  function render({ resetLimit = false } = {}) {
    if (!state.data) return;
    if (resetLimit) state.visibleLimit = PAGE_SIZE;
    const query = normalize(elements.search.value.trim());
    const papers = state.data.papers.filter((paper) => {
      if (!query) return true;
      return normalize([
        paper.title,
        paper.authors,
        paper.conference,
        paper.date,
        paper.doi,
      ].join(" ")).includes(query);
    });

    const order = elements.sort.value;
    if (order === "newest") {
      papers.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")) || a.source_order - b.source_order);
    } else if (order === "title") {
      papers.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" }));
    } else {
      papers.sort((a, b) => a.source_order - b.source_order);
    }

    const visible = papers.slice(0, state.visibleLimit);
    const fragment = document.createDocumentFragment();
    visible.forEach((paper) => {
      const row = document.createElement("tr");
      const titleCell = document.createElement("td");
      const title = document.createElement(isSafeUrl(paper.paper_url) ? "a" : "span");
      title.textContent = paper.title;
      if (title instanceof HTMLAnchorElement) {
        title.href = paper.paper_url;
        title.target = "_blank";
        title.rel = "noreferrer";
      }
      titleCell.append(title);
      if (paper.community_contribution) {
        const badge = document.createElement("span");
        badge.className = "complete-community-badge";
        badge.textContent = t("dynamic.community");
        badge.title = paper.contributor ? `Community contribution by ${paper.contributor}` : "Community contribution";
        titleCell.append(badge);
      }
      if (paper.authors) {
        const authors = document.createElement("small");
        authors.textContent = paper.authors;
        titleCell.append(authors);
      }

      const venueCell = document.createElement("td");
      const venue = document.createElement("span");
      venue.textContent = paper.conference || "—";
      venueCell.append(venue);
      if (paper.date) {
        const date = document.createElement("small");
        date.textContent = paper.date;
        venueCell.append(date);
      }

      const linksCell = document.createElement("td");
      linksCell.className = "complete-paper-links";
      appendLink(linksCell, t("dynamic.paper"), paper.paper_url);
      appendLink(linksCell, t("dynamic.project"), paper.project_url);
      appendLink(linksCell, t("dynamic.doi"), paper.doi_url);
      if (!linksCell.childElementCount) linksCell.textContent = "—";

      row.append(titleCell, venueCell, linksCell);
      fragment.append(row);
    });

    if (!papers.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 3;
      cell.className = "complete-empty";
      cell.textContent = t("dynamic.noResults");
      row.append(cell);
      fragment.append(row);
    }

    elements.list.replaceChildren(fragment);
    elements.list.setAttribute("aria-busy", "false");
    elements.count.textContent = papers.length.toLocaleString(locale());
    elements.loadMore.hidden = visible.length >= papers.length;
    if (!elements.loadMore.hidden) {
      const remaining = papers.length - visible.length;
      elements.loadMore.textContent = t("dynamic.loadMore", { count: remaining.toLocaleString(locale()) });
    }
  }

  async function initialize() {
    try {
      const response = await fetch("./assets/data/complete-list-data.json", { cache: "no-cache" });
      if (!response.ok) throw new Error(`Complete paper data request failed with status ${response.status}`);
      state.data = await response.json();
      elements.total.textContent = state.data.stats.paper_count.toLocaleString(locale());
      elements.generated.textContent = formatDate(state.data.meta.generated_at, t("dynamic.unknownTime"), locale());
      elements.search.addEventListener("input", () => render({ resetLimit: true }));
      elements.sort.addEventListener("change", () => render({ resetLimit: true }));
      elements.loadMore.addEventListener("click", () => {
        state.visibleLimit += PAGE_SIZE;
        render();
      });
      render();
    } catch (error) {
      console.error(error);
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 3;
      cell.className = "complete-empty";
      cell.textContent = t("dynamic.loadFailed");
      row.append(cell);
      elements.list.replaceChildren(row);
      elements.list.setAttribute("aria-busy", "false");
    }
  }

  setupNavigation({ header: elements.header, navToggle: elements.navToggle, nav: elements.nav });
  window.addEventListener("sim:languagechange", () => {
    if (!state.data) return;
    elements.total.textContent = state.data.stats.paper_count.toLocaleString(locale());
    elements.generated.textContent = formatDate(state.data.meta.generated_at, t("dynamic.unknownTime"), locale());
    render();
  });
  initialize();
})();
