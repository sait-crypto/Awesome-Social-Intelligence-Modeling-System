(() => {
  "use strict";

  const { formatDate, isSafeUrl, normalize, setupNavigation } = window.SIMSite;
  const i18n = window.SIMI18n;
  const t = (key, values) => i18n.t(key, values);
  const locale = () => (i18n.getLanguage() === "zh" ? "zh-CN" : "en");
  const stageLabel = (stage) =>
    i18n.getLanguage() === "zh" && ["Perception", "Understanding", "Generation", "Simulation"].includes(stage)
      ? t(`stage.${stage.toLowerCase()}`)
      : stage;
  const REPOSITORY_URL = "https://github.com/sait-crypto/Awesome-Social-Intelligence-Modeling-System";
  const RECENT_SUBMISSION_KEY = "sim-recent-paper-issue-draft";
  const RECENT_SUBMISSION_WINDOW = 10 * 60 * 1000;
  const PAGE_SIZE = 18;
  const STAGE_ORDER = ["Perception", "Understanding", "Generation", "Simulation", "Other", "Uncategorized"];
  const STAGE_TONES = {
    Perception: "#315ea8",
    Understanding: "#5578a8",
    Generation: "#6b82a5",
    Simulation: "#7d849b",
    Other: "#c8c5bd",
    Uncategorized: "#c8c5bd",
  };

  const state = {
    data: null,
    filtered: [],
    visibleLimit: PAGE_SIZE,
  };

  const elements = {
    header: document.querySelector("[data-header]"),
    navToggle: document.querySelector(".nav-toggle"),
    nav: document.querySelector(".primary-nav"),
    filterForm: document.querySelector("[data-filter-form]"),
    search: document.querySelector("#paper-search"),
    stage: document.querySelector("#stage-filter"),
    category: document.querySelector("#category-filter"),
    year: document.querySelector("#year-filter"),
    conference: document.querySelector("#conference-filter"),
    sort: document.querySelector("#sort-filter"),
    community: document.querySelector("#community-filter"),
    communityWrap: document.querySelector(".community-filter"),
    resultCount: document.querySelector("[data-result-count]"),
    activeFilters: document.querySelector("[data-active-filters]"),
    paperGrid: document.querySelector("[data-paper-grid]"),
    emptyState: document.querySelector("[data-empty-state]"),
    loadMore: document.querySelector("[data-load-more]"),
    cardTemplate: document.querySelector("#paper-card-template"),
    stageStats: document.querySelector("[data-stage-stats]"),
    taskBars: document.querySelector("[data-task-bars]"),
    timeline: document.querySelector("[data-timeline]"),
    submissionForm: document.querySelector("[data-submission-form]"),
    submissionCategories: document.querySelector("[data-submission-categories]"),
    categorySearch: document.querySelector("[data-category-search]"),
    categoryCount: document.querySelector("[data-category-count]"),
    zoteroDialog: document.querySelector("[data-zotero-dialog]"),
    zoteroOpen: document.querySelector("[data-open-zotero]"),
    zoteroClose: document.querySelectorAll("[data-close-zotero]"),
    zoteroJson: document.querySelector("[data-zotero-json]"),
    zoteroImport: document.querySelector("[data-import-zotero]"),
    zoteroStatus: document.querySelector("[data-zotero-status]"),
    zoteroInlineStatus: document.querySelector("[data-zotero-inline-status]"),
    doiGenerate: document.querySelector("[data-generate-doi]"),
    validationSummary: document.querySelector("[data-form-validation]"),
    pipelineImage: document.querySelector("[data-pipeline-image]"),
    pipelinePreview: document.querySelector("[data-pipeline-preview]"),
    pipelineStatus: document.querySelector("[data-pipeline-status]"),
    submitPaper: document.querySelector("[data-submit-paper]"),
    clearSubmission: document.querySelector("[data-clear-submission]"),
  };
  let submissionValidator = null;
  let submissionOpening = false;
  let pipelinePreviewUrl = "";

  const appendOption = (select, value, label) => {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = label;
    select.append(option);
  };

  const scrollToExplorer = () => {
    document.querySelector("#paper-explorer")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  function renderHeadlineStats() {
    const stats = state.data.stats;
    document.querySelectorAll('[data-stat="paper_count"]').forEach((node) => {
      node.textContent = new Intl.NumberFormat(locale()).format(stats.paper_count);
    });
    document.querySelectorAll('[data-stat="category_count"]').forEach((node) => {
      node.textContent = new Intl.NumberFormat(locale()).format(stats.category_count);
    });
    document.querySelectorAll("[data-generated-at]").forEach((node) => {
      node.textContent = t("dynamic.built", { date: formatDate(state.data.meta.generated_at, "Unknown build time", locale()) });
      node.setAttribute("datetime", state.data.meta.generated_at);
    });
    elements.communityWrap.hidden = stats.community_count === 0;
  }

  const mainStages = () => STAGE_ORDER.filter((stage) => !["Other", "Uncategorized"].includes(stage));

  function categoryRoot(categoryId) {
    const categoryById = new Map(state.data.categories.map((category) => [category.id, category]));
    let current = categoryById.get(categoryId);
    if (!current) return "";
    while (current.parent && categoryById.has(current.parent)) current = categoryById.get(current.parent);
    return current.id;
  }

  function updateSubmissionCategoryCount() {
    const count = elements.submissionCategories.querySelectorAll('input[type="checkbox"]:checked').length;
    elements.categoryCount.textContent = t("dynamic.selected", { count });
  }

  function renderStageStats(papers, selectedStage = "") {
    elements.stageStats.replaceChildren();

    mainStages().forEach((stage) => {
        const count = papers.filter((paper) => paper.stages.includes(stage)).length;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "stage-stat";
        button.dataset.stage = stage;
        button.style.setProperty("--stage-tone", STAGE_TONES[stage]);
        button.setAttribute("aria-pressed", String(selectedStage === stage));
        button.setAttribute("aria-label", `${stageLabel(stage)}: ${t("dynamic.papers", { count })}`);
        button.innerHTML = `<span>${stageLabel(stage)}</span><strong>${count}</strong><small>${t("dynamic.uniquePapers")}</small>`;
        button.addEventListener("click", () => setExplorerFilters({ stage: selectedStage === stage ? "" : stage }));
        elements.stageStats.append(button);
      });
  }

  function renderTaskBars(papers, selectedCategory = "") {
    const tasks = state.data.categories
      .filter((item) => item.leaf && item.depth > 0 && !["Other", "Uncategorized"].includes(item.id))
      .map((item) => ({
        ...item,
        stage: categoryRoot(item.id),
        count: papers.filter((paper) => paper.categories.includes(item.id)).length,
      }));
    elements.taskBars.replaceChildren();

    mainStages().forEach((stage) => {
      const stageTasks = tasks
        .filter((task) => task.stage === stage)
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
      if (!stageTasks.length) return;
      const maxCount = Math.max(...stageTasks.map((item) => item.count), 1);
      const panel = document.createElement("section");
      panel.className = "task-stage-panel";
      panel.style.setProperty("--stage-tone", STAGE_TONES[stage]);
      const heading = document.createElement("div");
      heading.className = "task-stage-heading";
      heading.innerHTML = `<h4>${stageLabel(stage)}</h4><span>${t("dynamic.tasks", { count: stageTasks.length })}</span>`;
      const list = document.createElement("div");
      list.className = "task-list";
      stageTasks.forEach((task) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "task-bar";
        button.setAttribute("aria-pressed", String(selectedCategory === task.id));
        button.setAttribute("aria-label", `${task.name}, ${t("dynamic.papers", { count: task.count })}`);

        const label = document.createElement("span");
        label.textContent = task.name;
        const track = document.createElement("span");
        track.className = "bar-track";
        const fill = document.createElement("i");
        fill.style.setProperty("--bar-width", `${task.count ? Math.max(4, (task.count / maxCount) * 100) : 0}%`);
        track.append(fill);
        const count = document.createElement("strong");
        count.textContent = task.count;
        button.append(label, track, count);
        button.addEventListener("click", () => {
          const active = selectedCategory === task.id;
          setExplorerFilters({ category: active ? "" : task.id, stage: active ? "" : task.stage });
        });
        list.append(button);
      });
      panel.append(heading, list);
      elements.taskBars.append(panel);
    });
  }

  function timelinePoint(paper) {
    const raw = String(paper.date || "").trim();
    const parts = raw.match(/^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?/);
    const year = Number(parts?.[1] || paper.year);
    if (!year) return null;
    const month = Math.min(12, Math.max(1, Number(parts?.[2] || 7)));
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const day = Math.min(daysInMonth, Math.max(1, Number(parts?.[3] || 15)));
    return {
      paper,
      time: Date.UTC(year, month - 1, day),
      year: String(year),
      label: parts?.[3]
        ? new Intl.DateTimeFormat(locale(), { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })
            .format(new Date(Date.UTC(year, month - 1, day)))
        : raw || String(year),
    };
  }

  function timelineTooltip() {
    let tooltip = document.querySelector("[data-timeline-tooltip]");
    if (tooltip) return tooltip;
    tooltip = document.createElement("div");
    tooltip.className = "coordinate-tip";
    tooltip.dataset.timelineTooltip = "";
    tooltip.setAttribute("role", "tooltip");
    document.body.append(tooltip);
    return tooltip;
  }

  function showTimelineTooltip(dot, event) {
    const tooltip = timelineTooltip();
    const name = document.createElement("strong");
    name.textContent = dot.dataset.paperTitle;
    const meta = document.createElement("span");
    meta.textContent = `${dot.dataset.paperStage} · ${dot.dataset.paperDate}`;
    tooltip.replaceChildren(name, meta);
    tooltip.classList.add("is-visible");
    moveTimelineTooltip(event);
  }

  function moveTimelineTooltip(event) {
    const tooltip = document.querySelector("[data-timeline-tooltip].is-visible");
    if (!tooltip || !event) return;
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = document.documentElement.clientHeight;
    const pointerX = event.clientX ?? 0;
    const pointerY = event.clientY ?? 0;
    let left = pointerX + 14;
    let top = pointerY - tooltip.offsetHeight - 14;
    if (left + tooltip.offsetWidth + 10 > viewportWidth) left = pointerX - tooltip.offsetWidth - 14;
    if (top < 8) top = pointerY + 18;
    left = Math.max(8, Math.min(left, viewportWidth - tooltip.offsetWidth - 8));
    top = Math.max(8, Math.min(top, viewportHeight - tooltip.offsetHeight - 8));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  function hideTimelineTooltip() {
    document.querySelector("[data-timeline-tooltip]")?.classList.remove("is-visible");
  }

  function renderTimeline(papers, selected = {}) {
    const timelineMinimum = Date.UTC(2021, 0, 1);
    const allPoints = state.data.papers
      .map(timelinePoint)
      .filter((point) => point && point.time >= timelineMinimum);
    const visiblePoints = papers
      .map(timelinePoint)
      .filter((point) => point && point.time >= timelineMinimum);
    if (!allPoints.length) return;
    const minimum = timelineMinimum;
    const maximum = Math.max(...allPoints.map((point) => point.time));
    const span = Math.max(1, maximum - minimum);
    const startYear = new Date(minimum).getUTCFullYear();
    const endYear = new Date(maximum).getUTCFullYear();
    const position = (time) => Math.max(0, Math.min(100, ((time - minimum) / span) * 100));
    const years = Array.from({ length: endYear - startYear + 1 }, (_, index) => String(startYear + index));
    const jitter = [0, -9, 9, -17, 17, -5, 5, -13, 13];

    elements.timeline.replaceChildren();
    const plot = document.createElement("div");
    plot.className = "coordinate-plot";

    mainStages().forEach((stage) => {
      const lanePoints = visiblePoints
        .filter((point) => point.paper.stages.includes(stage))
        .sort((a, b) => a.time - b.time || a.paper.title.localeCompare(b.paper.title));
      const lane = document.createElement("section");
      lane.className = "coordinate-lane";
      lane.style.setProperty("--stage-tone", STAGE_TONES[stage]);

      const heading = document.createElement("button");
      heading.type = "button";
      heading.className = "coordinate-lane-heading";
      heading.setAttribute("aria-pressed", String(selected.stage === stage));
      heading.setAttribute("aria-label", `${stageLabel(stage)}: ${t("dynamic.papers", { count: lanePoints.length })}`);
      const stageName = document.createElement("strong");
      stageName.textContent = stageLabel(stage);
      const count = document.createElement("span");
      count.textContent = t("dynamic.papers", { count: lanePoints.length });
      heading.append(stageName, count);
      heading.addEventListener("click", () => setExplorerFilters({ stage: selected.stage === stage ? "" : stage }));

      const track = document.createElement("div");
      track.className = "coordinate-track";
      years.slice(1).forEach((year) => {
        const line = document.createElement("i");
        line.className = "coordinate-gridline";
        line.style.left = `${position(Date.UTC(Number(year), 0, 1))}%`;
        track.append(line);
      });
      lanePoints.forEach((point, index) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "coordinate-dot";
        dot.style.left = `${position(point.time)}%`;
        dot.style.top = `calc(50% + ${jitter[index % jitter.length]}px)`;
        dot.dataset.paperTitle = point.paper.title;
        dot.dataset.paperStage = stageLabel(stage);
        dot.dataset.paperDate = point.label;
        dot.setAttribute("aria-label", `${point.paper.title}, ${stageLabel(stage)}, ${point.label}`);
        dot.classList.toggle("is-selected", selected.stage === stage && selected.year === point.year);
        dot.addEventListener("pointerenter", (event) => showTimelineTooltip(dot, event));
        dot.addEventListener("pointermove", moveTimelineTooltip);
        dot.addEventListener("pointerleave", hideTimelineTooltip);
        dot.addEventListener("focus", () => {
          const rect = dot.getBoundingClientRect();
          showTimelineTooltip(dot, { clientX: rect.left + rect.width / 2, clientY: rect.top });
        });
        dot.addEventListener("blur", hideTimelineTooltip);
        dot.addEventListener("click", () => setExplorerFilters({ stage, year: point.year }));
        track.append(dot);
      });
      lane.append(heading, track);
      plot.append(lane);
    });

    const axis = document.createElement("div");
    axis.className = "coordinate-axis";
    const axisTitle = document.createElement("span");
    axisTitle.className = "coordinate-axis-title";
    axisTitle.textContent = t("dynamic.publicationYear");
    const axisTrack = document.createElement("div");
    axisTrack.className = "coordinate-axis-track";
    years.forEach((year) => {
      const tick = document.createElement("button");
      tick.type = "button";
      tick.className = "coordinate-year";
      tick.style.left = `${position(Date.UTC(Number(year), 0, 1))}%`;
      tick.textContent = year;
      tick.setAttribute("aria-pressed", String(selected.year === year));
      tick.addEventListener("click", () => setExplorerFilters({ year: selected.year === year ? "" : year }));
      axisTrack.append(tick);
    });
    axis.append(axisTitle, axisTrack);
    plot.append(axis);
    elements.timeline.append(plot);
  }

  function populateFilters() {
    const stageNames = state.data.stats.stages
      .map((item) => item.name)
      .sort((a, b) => STAGE_ORDER.indexOf(a) - STAGE_ORDER.indexOf(b));
    stageNames.forEach((stage) => appendOption(elements.stage, stage, stage));

    const categoryById = new Map(state.data.categories.map((category) => [category.id, category]));
    const categoryPath = (category) => {
      const path = [category.name];
      let parent = categoryById.get(category.parent);
      while (parent) {
        path.unshift(parent.name);
        parent = categoryById.get(parent.parent);
      }
      return path.join(" › ");
    };
    state.data.categories
      .filter((category) => category.count > 0 && category.depth > 0)
      .sort((a, b) => categoryPath(a).localeCompare(categoryPath(b)))
      .forEach((category) => appendOption(elements.category, category.id, `${categoryPath(category)} (${category.count})`));

    [...state.data.stats.years]
      .sort((a, b) => Number(b.name) - Number(a.name))
      .forEach((year) => appendOption(elements.year, year.name, `${year.name} (${year.count})`));

    state.data.stats.conferences.forEach((conference) => {
      appendOption(elements.conference, conference.name, `${conference.name} (${conference.count})`);
    });
  }

  function renderSubmissionCategories() {
    elements.submissionCategories.replaceChildren();
    const categoryById = new Map(state.data.categories.map((category) => [category.id, category]));
    const selectable = state.data.categories.filter(
      (category) => category.leaf && !["Other", "Uncategorized"].includes(category.id),
    );

    const rootFor = (category) => {
      let current = category;
      while (current.parent && categoryById.has(current.parent)) current = categoryById.get(current.parent);
      return current.id;
    };
    const pathFor = (category) => {
      const path = [];
      let current = category;
      while (current) {
        path.unshift(current.name);
        current = categoryById.get(current.parent);
      }
      return path;
    };
    STAGE_ORDER.filter((stage) => !["Other", "Uncategorized"].includes(stage)).forEach((stage, stageIndex) => {
      const stageCategories = selectable.filter((category) => rootFor(category) === stage);
      if (!stageCategories.length) return;
      const details = document.createElement("details");
      details.className = "category-stage";
      details.open = stageIndex === 0;
      details.dataset.stage = stage;
      const summary = document.createElement("summary");
      const stageName = document.createElement("strong");
      stageName.textContent = stageLabel(stage);
      const stageCount = document.createElement("span");
      stageCount.textContent = t("dynamic.tasks", { count: stageCategories.length });
      summary.append(stageName, stageCount);
      const groups = document.createElement("div");
      groups.className = "category-groups";

      const grouped = new Map();
      stageCategories.forEach((category) => {
        const path = pathFor(category);
        const groupName = path.slice(1, -1).join(" › ") || stage;
        if (!grouped.has(groupName)) grouped.set(groupName, []);
        grouped.get(groupName).push(category);
      });
      [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)).forEach(([groupName, categories]) => {
        const group = document.createElement("section");
        group.className = "category-group";
        const heading = document.createElement("h4");
        heading.textContent = groupName;
        group.append(heading);
        categories.sort((a, b) => a.name.localeCompare(b.name)).forEach((category) => {
        const label = document.createElement("label");
        label.className = "submission-category";
        label.dataset.search = normalize(`${stage} ${groupName} ${category.name}`);
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "categories";
        input.value = category.id;
        const text = document.createElement("span");
        text.textContent = category.name;
        input.addEventListener("change", () => {
          const checked = elements.submissionCategories.querySelectorAll('input[type="checkbox"]:checked');
          if (checked.length > 4) {
            input.checked = false;
            window.alert(t("dynamic.categoryLimit"));
          }
          updateSubmissionCategoryCount();
        });
        label.append(input, text);
          group.append(label);
        });
        groups.append(group);
      });
      details.append(summary, groups);
      elements.submissionCategories.append(details);
    });

    elements.categorySearch.addEventListener("input", () => {
      const query = normalize(elements.categorySearch.value.trim());
      elements.submissionCategories.querySelectorAll(".submission-category").forEach((label) => {
        label.hidden = Boolean(query) && !label.dataset.search.includes(query);
      });
      elements.submissionCategories.querySelectorAll(".category-group").forEach((group) => {
        group.hidden = ![...group.querySelectorAll(".submission-category")].some((label) => !label.hidden);
      });
      elements.submissionCategories.querySelectorAll(".category-stage").forEach((details) => {
        const hasMatch = [...details.querySelectorAll(".category-group")].some((group) => !group.hidden);
        details.hidden = !hasMatch;
        if (query && hasMatch) details.open = true;
      });
    });
    updateSubmissionCategoryCount();
  }

  const controls = () => ({
    q: elements.search.value.trim(),
    stage: elements.stage.value,
    category: elements.category.value,
    year: elements.year.value,
    conference: elements.conference.value,
    sort: elements.sort.value,
    community: elements.community.checked,
  });

  function updateUrl(values) {
    const params = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (key === "sort" && value === "newest") return;
      if (value) params.set(key, String(value === true ? 1 : value));
    });
    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
    window.history.replaceState(null, "", url);
  }

  function restoreFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    elements.search.value = params.get("q") || "";
    elements.stage.value = params.get("stage") || "";
    elements.category.value = params.get("category") || "";
    elements.year.value = params.get("year") || "";
    elements.conference.value = params.get("conference") || "";
    elements.sort.value = params.get("sort") || "newest";
    elements.community.checked = params.get("community") === "1";
  }

  function paperMatches(paper, values, ignored = []) {
    const ignore = new Set(ignored);
    const tokens = normalize(values.q).split(/\s+/).filter(Boolean);
    if (!ignore.has("stage") && values.stage && !paper.stages.includes(values.stage)) return false;
    if (!ignore.has("category") && values.category && !paper.categories.includes(values.category)) return false;
    if (!ignore.has("year") && values.year && String(paper.year || "") !== values.year) return false;
    if (!ignore.has("conference") && values.conference && paper.conference !== values.conference) return false;
    if (!ignore.has("community") && values.community && !paper.community_contribution) return false;
    if (!ignore.has("q") && tokens.length) {
      const haystack = normalize(
        [
          paper.title,
          paper.title_translation,
          paper.authors,
          paper.conference,
          paper.categories.join(" "),
          paper.analogy_summary,
          paper.abstract,
          paper.doi,
          paper.contributor,
        ].join(" "),
      );
      if (!tokens.every((token) => haystack.includes(token))) return false;
    }
    return true;
  }

  function filterPapers({ resetLimit = true } = {}) {
    if (!state.data) return;
    const values = controls();
    const filtered = state.data.papers.filter((paper) => paperMatches(paper, values));

    filtered.sort((a, b) => {
      if (values.sort === "title") return a.title.localeCompare(b.title);
      const dateCompare = String(a.date || "").localeCompare(String(b.date || ""));
      return values.sort === "oldest" ? dateCompare : -dateCompare;
    });

    state.filtered = filtered;
    if (resetLimit) state.visibleLimit = PAGE_SIZE;
    updateUrl(values);
    renderPapers();
    renderActiveFilters(values);
    renderStageStats(state.data.papers, values.stage);
    renderTaskBars(state.data.papers, values.category);
    renderTimeline(state.data.papers, values);
  }

  function makePaperLink(label, url) {
    if (!isSafeUrl(url)) return null;
    const link = document.createElement("a");
    link.className = "paper-link";
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = `${label} ↗`;
    return link;
  }

  function renderPaperCard(paper) {
    const card = elements.cardTemplate.content.firstElementChild.cloneNode(true);
    const meta = card.querySelector(".paper-meta");
    meta.textContent = [paper.year || t("dynamic.undated"), paper.conference || t("dynamic.unspecifiedVenue")].join(" · ");

    const badge = card.querySelector(".community-badge");
    badge.hidden = !paper.community_contribution;

    const heading = card.querySelector("h3");
    if (isSafeUrl(paper.paper_url)) {
      const link = document.createElement("a");
      link.href = paper.paper_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = paper.title;
      heading.append(link);
    } else {
      heading.textContent = paper.title;
    }

    card.querySelector(".paper-authors").textContent = paper.authors || t("dynamic.authorsMissing");
    const tags = card.querySelector(".paper-tags");
    paper.categories.slice(0, 4).forEach((category) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "paper-tag";
      button.textContent = category;
      button.title = `Filter to ${category}`;
      button.addEventListener("click", () => setExplorerFilter("category", category));
      tags.append(button);
    });

    const summary = card.querySelector(".paper-summary");
    if (paper.analogy_summary) {
      summary.hidden = false;
      summary.querySelector("span").textContent = paper.analogy_summary;
    }
    const abstract = card.querySelector(".paper-abstract");
    if (paper.abstract) {
      abstract.hidden = false;
      abstract.querySelector("span").textContent = paper.abstract;
    }
    const contributor = card.querySelector(".paper-contributor");
    if (paper.community_contribution) {
      contributor.hidden = false;
      contributor.textContent = t("dynamic.communityContribution", { contributor: paper.contributor });
    }

    const links = card.querySelector(".paper-links");
    [makePaperLink(t("dynamic.paper"), paper.paper_url), makePaperLink(t("dynamic.project"), paper.project_url)]
      .filter(Boolean)
      .forEach((link) => links.append(link));
    i18n.apply(card);
    return card;
  }

  function renderPapers() {
    const visible = state.filtered.slice(0, state.visibleLimit);
    elements.paperGrid.replaceChildren(...visible.map(renderPaperCard));
    elements.paperGrid.setAttribute("aria-busy", "false");
    elements.resultCount.textContent = new Intl.NumberFormat(locale()).format(state.filtered.length);
    elements.emptyState.hidden = state.filtered.length !== 0;
    elements.paperGrid.hidden = state.filtered.length === 0;
    elements.loadMore.hidden = state.visibleLimit >= state.filtered.length;
    if (!elements.loadMore.hidden) {
      const remaining = state.filtered.length - state.visibleLimit;
      elements.loadMore.textContent = t("dynamic.loadMore", { count: remaining });
    }
  }

  function renderActiveFilters(values) {
    elements.activeFilters.replaceChildren();
    const items = [
      ["q", values.q, t("dynamic.filterSearch")],
      ["stage", values.stage, t("dynamic.filterField")],
      ["category", values.category, t("dynamic.filterTask")],
      ["year", values.year, t("dynamic.filterYear")],
      ["conference", values.conference, t("dynamic.filterVenue")],
      ["community", values.community ? t("dynamic.community") : "", t("dynamic.filterSource")],
    ].filter((item) => item[1]);

    items.forEach(([key, value, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "filter-chip";
      button.append(document.createTextNode(`${label}: ${String(value)} `));
      const close = document.createElement("span");
      close.setAttribute("aria-hidden", "true");
      close.textContent = "×";
      button.append(close);
      button.setAttribute("aria-label", t("dynamic.removeFilter", { label, value }));
      button.addEventListener("click", () => clearSingleFilter(key));
      elements.activeFilters.append(button);
    });
  }

  function clearSingleFilter(key) {
    if (key === "q") elements.search.value = "";
    else if (key === "community") elements.community.checked = false;
    else if (elements[key]) elements[key].value = "";
    filterPapers();
  }

  function clearFilters() {
    elements.filterForm.reset();
    elements.sort.value = "newest";
    filterPapers();
  }

  function setExplorerFilters(patch) {
    if (!state.data) return;
    hideTimelineTooltip();
    Object.entries(patch).forEach(([key, value]) => {
      if (elements[key]) elements[key].value = String(value);
    });
    if (Object.prototype.hasOwnProperty.call(patch, "category") && patch.category) {
      elements.stage.value = categoryRoot(String(patch.category));
    } else if (Object.prototype.hasOwnProperty.call(patch, "stage") && patch.stage && elements.category.value) {
      if (categoryRoot(elements.category.value) !== String(patch.stage)) elements.category.value = "";
    }
    filterPapers();
    scrollToExplorer();
  }

  function setExplorerFilter(key, value) {
    setExplorerFilters({ [key]: value });
  }

  function debounce(callback, wait = 170) {
    let timeout;
    return (...args) => {
      window.clearTimeout(timeout);
      timeout = window.setTimeout(() => callback(...args), wait);
    };
  }

  function setupExplorerEvents() {
    elements.search.addEventListener("input", debounce(() => filterPapers()));
    [elements.stage, elements.category, elements.year, elements.conference, elements.sort, elements.community].forEach(
      (control) => control.addEventListener("change", () => filterPapers()),
    );
    elements.filterForm.addEventListener("reset", () => window.setTimeout(clearFilters, 0));
    document.querySelectorAll("[data-clear-filters]").forEach((button) => button.addEventListener("click", clearFilters));
    elements.loadMore.addEventListener("click", () => {
      state.visibleLimit += PAGE_SIZE;
      renderPapers();
    });
    document.querySelectorAll("[data-stage-filter]").forEach((button) => {
      button.addEventListener("click", () => setExplorerFilter("stage", button.dataset.stageFilter));
    });
    document.addEventListener("keydown", (event) => {
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      if (event.key === "/" && !["input", "textarea", "select"].includes(activeTag)) {
        event.preventDefault();
        elements.search.focus();
      }
    });
  }

  const cleanIssueValue = (value, maxLength = 5000) => {
    const text = String(value || "").replace(/\r\n/g, "\n").trim();
    return text.length > maxLength ? `${text.slice(0, maxLength - 1).trim()}…` : text;
  };

  function buildIssueBody(formData, categories) {
    const pipelineFile = formData.get("pipeline_image_file");
    const hasPipelineImage = pipelineFile instanceof File && pipelineFile.size > 0;
    const fields = [
      ["Paper title", formData.get("title")],
      ["DOI", formData.get("doi")],
      ["Paper URL", formData.get("paper_url")],
      ["Project URL", formData.get("project_url") || "_No response_"],
      ["Authors", formData.get("authors")],
      ["Publication date", formData.get("date")],
      ["Venue", formData.get("venue") || "_No response_"],
      ["Contributor", formData.get("contributor") || "_No response_"],
      ["Categories", categories.join(" | ")],
      ["Abstract", cleanIssueValue(formData.get("abstract"), 2600)],
      [
        "Pipeline image",
        hasPipelineImage
          ? "_Paste or drag the selected pipeline image here before submitting this issue._"
          : "_No response_",
      ],
      ["Citation key", formData.get("citation_key") || "_No response_"],
      ["Translated title", formData.get("title_translation") || "_No response_"],
      ["Analogy summary", cleanIssueValue(formData.get("analogy_summary"), 1000) || "_No response_"],
      ["Motivation", cleanIssueValue(formData.get("summary_motivation"), 1800) || "_No response_"],
      ["Innovation", cleanIssueValue(formData.get("summary_innovation"), 1800) || "_No response_"],
      ["Method", cleanIssueValue(formData.get("summary_method"), 1800) || "_No response_"],
      ["Conclusion / contribution", cleanIssueValue(formData.get("summary_conclusion"), 1800) || "_No response_"],
      ["Limitations / future work", cleanIssueValue(formData.get("summary_limitation"), 1800) || "_No response_"],
      ["Citable paragraph", cleanIssueValue(formData.get("summary_citable_paragraph"), 2800) || "_No response_"],
      ["Related papers", cleanIssueValue(formData.get("related_papers"), 1500) || "_No response_"],
      ["Additional notes", cleanIssueValue(formData.get("notes"), 650) || "_No response_"],
    ];
    return [
      "<!-- sim-paper-submission:v1 -->",
      ...fields.flatMap(([heading, value]) => [`### ${heading}`, cleanIssueValue(value), ""]),
      "---",
      "Submitted through the Social Intelligence Modeling survey homepage.",
    ].join("\n");
  }

  function setupZoteroImport() {
    const setField = (name, value) => {
      if (value === undefined || value === null || String(value).trim() === "") return;
      const field = elements.submissionForm.elements.namedItem(name);
      if (field) {
        field.value = String(value).trim();
        field.dispatchEvent(new Event("input", { bubbles: true }));
      }
    };
    const extraValue = (extra, label) => {
      const match = String(extra || "").match(new RegExp(`^${label}\\s*:\\s*(.+)$`, "im"));
      return match ? match[1].trim() : "";
    };
    const itemValue = (item, snakeName, camelName = snakeName) => item[snakeName] || item[camelName] || "";
    const closeDialog = () => {
      if (elements.zoteroDialog?.open) elements.zoteroDialog.close();
    };
    const importJson = () => {
      try {
        const parsed = JSON.parse(elements.zoteroJson.value.trim());
        const items = Array.isArray(parsed) ? parsed : [parsed];
        if (items.length !== 1 || !items[0] || typeof items[0] !== "object") {
          throw new Error(t("zotero.singleError"));
        }
        const item = items[0];
        const authors = (item.creators || [])
          .map((creator) => creator.name || [creator.firstName, creator.lastName].filter(Boolean).join(" "))
          .filter(Boolean)
          .join(", ");
        const doi = String(item.DOI || "").replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "");
        const paperUrl = item.url || (doi ? `https://doi.org/${doi}` : "");
        const venue =
          item.journalAbbreviation || item.conferenceName || item.proceedingsTitle ||
          item.publicationTitle || item.bookTitle || item.series || "";

        setField("title", item.title);
        setField("doi", doi);
        setField("date", item.date);
        setField("paper_url", paperUrl);
        setField("project_url", extraValue(item.extra, "(?:Project URL|Code URL)"));
        setField("authors", authors);
        setField("venue", venue);
        setField("contributor", item.contributor);
        setField("abstract", item.abstractNote);
        setField("citation_key", item.citationKey || extraValue(item.extra, "Citation Key"));
        setField(
          "title_translation",
          itemValue(item, "title_translation", "titleTranslation") || extraValue(item.extra, "titleTranslation"),
        );
        setField(
          "analogy_summary",
          itemValue(item, "analogy_summary", "analogySummary") || extraValue(item.extra, "(?:TLDR|Analogy Summary)"),
        );
        setField("summary_motivation", itemValue(item, "summary_motivation", "summaryMotivation"));
        setField("summary_innovation", itemValue(item, "summary_innovation", "summaryInnovation"));
        setField("summary_method", itemValue(item, "summary_method", "summaryMethod"));
        setField("summary_conclusion", itemValue(item, "summary_conclusion", "summaryConclusion"));
        setField("summary_limitation", itemValue(item, "summary_limitation", "summaryLimitation"));
        setField(
          "summary_citable_paragraph",
          itemValue(item, "summary_citable_paragraph", "summaryCitableParagraph"),
        );
        setField("related_papers", itemValue(item, "related_papers", "relatedPapers"));
        const importedNotes = Array.isArray(item.notes)
          ? item.notes
              .map((note) => (typeof note === "string" ? note : note?.note || ""))
              .filter(Boolean)
              .join("\n")
          : item.notes;
        setField("notes", importedNotes);

        const activeByName = new Map(
          [...elements.submissionCategories.querySelectorAll('input[name="categories"]')].map((input) => [normalize(input.value), input]),
        );
        const importedCategories = (item.tags || [])
          .map((tag) => String(tag.tag || tag).trim())
          .filter((tag) => /^cat\s+/i.test(tag))
          .flatMap((tag) => tag.replace(/^cat\s+/i, "").split(/[|;；]/))
          .map((tag) => tag.trim())
          .filter(Boolean);
        let matchedCategories = 0;
        importedCategories.slice(0, 4).forEach((category) => {
          const input = activeByName.get(normalize(category));
          if (input) {
            input.checked = true;
            input.dispatchEvent(new Event("change", { bubbles: true }));
            input.closest("details")?.setAttribute("open", "");
            matchedCategories += 1;
          }
        });
        const categoryMessage = importedCategories.length && !matchedCategories
          ? ` ${t("zotero.categoryUnrecognized")}`
          : "";
        elements.zoteroStatus.textContent = `${t(item.title ? "zotero.importedPaper" : "zotero.importedAvailable")}${categoryMessage}`;
        elements.zoteroStatus.dataset.state = "success";
        elements.zoteroInlineStatus.textContent = item.title ? `${t("zotero.importedPaper")} · ${item.title}` : t("zotero.inlineImported");
        elements.zoteroInlineStatus.dataset.state = "success";
        closeDialog();
      } catch (error) {
        elements.zoteroStatus.textContent = error instanceof SyntaxError
          ? t("zotero.readError")
          : error instanceof Error ? error.message : t("zotero.readError");
        elements.zoteroStatus.dataset.state = "error";
      }
    };

    elements.zoteroImport.addEventListener("click", importJson);
    elements.zoteroOpen.addEventListener("click", () => {
      elements.zoteroStatus.textContent = "";
      delete elements.zoteroStatus.dataset.state;
      elements.zoteroDialog.showModal();
      window.setTimeout(() => elements.zoteroJson.focus(), 0);
    });
    elements.zoteroClose.forEach((button) => button.addEventListener("click", closeDialog));
    elements.zoteroDialog.addEventListener("click", (event) => {
      if (event.target === elements.zoteroDialog) closeDialog();
    });
    elements.zoteroJson.addEventListener("paste", () => {
      window.setTimeout(() => {
        elements.zoteroStatus.textContent = t("zotero.pasted");
        delete elements.zoteroStatus.dataset.state;
      }, 0);
    });
  }

  function setupDoiPlaceholder() {
    elements.doiGenerate.addEventListener("click", () => {
      const doiField = elements.submissionForm.elements.namedItem("doi");
      if (doiField.value.trim() && !window.confirm(t("doi.replace"))) return;
      const title = elements.submissionForm.elements.namedItem("title").value;
      const slug = normalize(title)
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "")
        .slice(0, 32) || "untitled";
      const token = Date.now().toString(36).slice(-6);
      doiField.value = `10.0000/placeholder-${slug}-${token}`;
      doiField.dispatchEvent(new Event("input", { bubbles: true }));
      doiField.focus();
    });
  }

  function setupPipelineImage() {
    if (!elements.pipelineImage) return;
    const allowedTypes = new Set(["image/png", "image/jpeg", "image/gif", "image/webp"]);
    elements.pipelineImage.addEventListener("change", () => {
      if (pipelinePreviewUrl) URL.revokeObjectURL(pipelinePreviewUrl);
      pipelinePreviewUrl = "";
      elements.pipelineImage.setCustomValidity("");
      const file = elements.pipelineImage.files?.[0];
      if (!file) {
        elements.pipelinePreview.hidden = true;
        return;
      }
      if (!allowedTypes.has(file.type)) {
        elements.pipelineImage.setCustomValidity(t("pipeline.unsupported"));
      } else if (file.size > 10 * 1024 * 1024) {
        elements.pipelineImage.setCustomValidity(t("pipeline.tooLarge"));
      }
      if (elements.pipelineImage.validationMessage) {
        elements.pipelineStatus.textContent = elements.pipelineImage.validationMessage;
        elements.pipelinePreview.querySelector("img").removeAttribute("src");
      } else {
        pipelinePreviewUrl = URL.createObjectURL(file);
        elements.pipelinePreview.querySelector("img").src = pipelinePreviewUrl;
        elements.pipelineStatus.textContent = t("pipeline.selected", { name: file.name });
      }
      elements.pipelinePreview.hidden = false;
    });
  }

  async function copyPipelineImage(file) {
    if (!(file instanceof File) || !navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
      return false;
    }
    try {
      await navigator.clipboard.write([new ClipboardItem({ [file.type]: file })]);
      return true;
    } catch (_error) {
      return false;
    }
  }

  const submissionFingerprint = (formData) =>
    `${cleanIssueValue(formData.get("doi"), 180).toLowerCase()}|${cleanIssueValue(formData.get("title"), 500).toLowerCase()}`;

  function recentlyOpenedSameSubmission(fingerprint) {
    try {
      const recent = JSON.parse(window.localStorage.getItem(RECENT_SUBMISSION_KEY) || "null");
      return recent?.fingerprint === fingerprint && Date.now() - Number(recent.openedAt || 0) < RECENT_SUBMISSION_WINDOW;
    } catch (_error) {
      return false;
    }
  }

  function rememberSubmissionDraft(fingerprint) {
    try {
      window.localStorage.setItem(RECENT_SUBMISSION_KEY, JSON.stringify({ fingerprint, openedAt: Date.now() }));
    } catch (_error) {
      // Submission can continue when storage is unavailable.
    }
  }

  function setupSubmissionForm() {
    elements.submissionForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (submissionOpening) return;
      if (submissionValidator && !submissionValidator.validate()) return;
      if (!elements.submissionForm.reportValidity()) return;

      const checked = [...elements.submissionCategories.querySelectorAll('input[type="checkbox"]:checked')];

      const formData = new FormData(elements.submissionForm);
      const fingerprint = submissionFingerprint(formData);
      if (recentlyOpenedSameSubmission(fingerprint) && !window.confirm(t("submission.duplicateDraft"))) return;

      const categories = checked.map((input) => input.value);
      const title = `[Paper Submission] ${cleanIssueValue(formData.get("title"), 180)}`;
      const body = buildIssueBody(formData, categories);
      const params = new URLSearchParams({ title, body });
      const issueUrl = `${REPOSITORY_URL}/issues/new?${params.toString()}`;
      const pipelineFile = formData.get("pipeline_image_file");
      submissionOpening = true;
      elements.submitPaper.disabled = true;
      const releaseButton = () => window.setTimeout(() => {
        submissionOpening = false;
        elements.submitPaper.disabled = false;
      }, 2500);

      if (issueUrl.length > 7900 && navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(body);
          rememberSubmissionDraft(fingerprint);
          window.alert(t("submission.long"));
          window.open(`${REPOSITORY_URL}/issues/new?${new URLSearchParams({ title }).toString()}`, "_blank", "noopener");
          releaseButton();
          return;
        } catch (_error) {
          // Fall through to GitHub's prefilled URL when clipboard access is unavailable.
        }
      }
      const imageCopy = pipelineFile instanceof File && pipelineFile.size > 0
        ? copyPipelineImage(pipelineFile)
        : null;
      rememberSubmissionDraft(fingerprint);
      window.open(issueUrl, "_blank", "noopener");
      if (imageCopy) {
        window.alert(t((await imageCopy) ? "pipeline.copied" : "pipeline.copyUnavailable"));
      }
      releaseButton();
    });
  }

  function setupSubmissionClear() {
    elements.clearSubmission?.addEventListener("click", () => {
      if (!window.confirm(t("submission.clearConfirm"))) return;
      elements.submissionForm.reset();
      submissionValidator?.reset?.();
      elements.categorySearch.value = "";
      elements.submissionCategories.querySelectorAll(".submission-category, .category-group, .category-stage").forEach((node) => {
        node.hidden = false;
      });
      elements.submissionCategories.querySelectorAll(".category-stage").forEach((details, index) => {
        details.open = index === 0;
      });
      updateSubmissionCategoryCount();
      if (pipelinePreviewUrl) URL.revokeObjectURL(pipelinePreviewUrl);
      pipelinePreviewUrl = "";
      elements.pipelineImage.setCustomValidity("");
      elements.pipelinePreview.hidden = true;
      elements.pipelinePreview.querySelector("img").removeAttribute("src");
      elements.pipelineStatus.textContent = "";
      elements.zoteroJson.value = "";
      elements.zoteroStatus.textContent = "";
      delete elements.zoteroStatus.dataset.state;
      elements.zoteroInlineStatus.textContent = t("form.zoteroHint");
      delete elements.zoteroInlineStatus.dataset.state;
      elements.submissionForm.querySelectorAll("details.optional-fields").forEach((details) => {
        details.open = false;
      });
    });
  }

  function renderLoadError(error) {
    console.error(error);
    elements.paperGrid.setAttribute("aria-busy", "false");
    const message = document.createElement("div");
    message.className = "paper-loading";
    message.append(document.createTextNode(`${t("dynamic.loadFailed")} `));
    const repositoryLink = document.createElement("a");
    repositoryLink.href = REPOSITORY_URL;
    repositoryLink.textContent = t("dynamic.openRepository");
    message.append(repositoryLink, document.createTextNode(` ${t("dynamic.refreshPage")}`));
    elements.paperGrid.replaceChildren(message);
    if (elements.stageStats) {
      const unavailable = document.createElement("div");
      unavailable.className = "loading-card";
      unavailable.textContent = t("dynamic.taxonomyUnavailable");
      elements.stageStats.replaceChildren(unavailable);
    }
  }

  async function initializeData() {
    try {
      const response = await fetch("./assets/data/site-data.json", { cache: "no-cache" });
      if (!response.ok) throw new Error(`Paper data request failed with status ${response.status}`);
      state.data = await response.json();
      renderHeadlineStats();
      populateFilters();
      renderSubmissionCategories();
      submissionValidator = window.SIMFormValidation?.create({
        form: elements.submissionForm,
        categoryContainer: elements.submissionCategories,
        summary: elements.validationSummary,
      });
      setupZoteroImport();
      setupDoiPlaceholder();
      setupPipelineImage();
      restoreFiltersFromUrl();
      setupExplorerEvents();
      setupSubmissionForm();
      setupSubmissionClear();
      filterPapers();
    } catch (error) {
      renderLoadError(error);
    }
  }

  function refreshDynamicLanguage() {
    if (!state.data) return;
    renderHeadlineStats();
    updateSubmissionCategoryCount();
    elements.submissionCategories.querySelectorAll(".category-stage").forEach((details) => {
      const stage = details.dataset.stage;
      details.querySelector("summary strong").textContent = stageLabel(stage);
      const count = details.querySelectorAll(".submission-category").length;
      details.querySelector("summary span").textContent = t("dynamic.tasks", { count });
    });
    filterPapers({ resetLimit: false });
  }

  setupNavigation({ header: elements.header, navToggle: elements.navToggle, nav: elements.nav });
  window.addEventListener("sim:languagechange", refreshDynamicLanguage);
  initializeData();
})();
