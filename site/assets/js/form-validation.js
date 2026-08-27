(() => {
  "use strict";

  const t = (key, values) => window.SIMI18n.t(key, values);
  const DOI_PATTERN = /^10\.\d{4,9}\/\S+$/i;
  const DATE_PATTERN = /^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$/;
  const REQUIRED_FIELDS = [
    ["title", "validation.titleRequired"],
    ["doi", "validation.doiRequired"],
    ["date", "validation.dateRequired"],
    ["paper_url", "validation.paperUrlRequired"],
    ["authors", "validation.authorsRequired"],
    ["abstract", "validation.abstractRequired"],
  ];

  const fieldValue = (form, name) => String(form.elements.namedItem(name)?.value || "").trim();

  function create({ form, categoryContainer, summary }) {
    if (!form || !categoryContainer || !summary) return null;
    let attempted = false;
    const categoryFieldset = categoryContainer.closest("fieldset");

    const setFieldValidity = (name, message) => {
      const field = form.elements.namedItem(name);
      if (!field || typeof field.setCustomValidity !== "function") return;
      field.setCustomValidity(message || "");
      field.setAttribute("aria-invalid", message ? "true" : "false");
    };

    const collectErrors = () => {
      const errors = [];
      REQUIRED_FIELDS.forEach(([name, messageKey]) => {
        const requiredError = fieldValue(form, name) ? "" : t(messageKey);
        setFieldValidity(name, requiredError);
        if (requiredError) errors.push({ name, message: requiredError });
      });

      const doi = fieldValue(form, "doi").replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "");
      const doiError = doi && !DOI_PATTERN.test(doi) ? t("validation.doiFormat") : "";
      setFieldValidity("doi", doiError);
      if (doiError) errors.push({ name: "doi", message: doiError });

      const date = fieldValue(form, "date");
      const dateError = date && !DATE_PATTERN.test(date) ? t("validation.dateFormat") : "";
      setFieldValidity("date", dateError);
      if (dateError) errors.push({ name: "date", message: dateError });

      [
        ["paper_url", "validation.paperUrl"],
        ["project_url", "validation.projectUrl"],
      ].forEach(([name, labelKey]) => {
        const value = fieldValue(form, name);
        const urlError = value && !/^https?:\/\/\S+$/i.test(value)
          ? t("validation.urlFormat", { label: t(labelKey) })
          : "";
        setFieldValidity(name, urlError);
        if (urlError) errors.push({ name, message: urlError });
      });

      const checked = categoryContainer.querySelectorAll('input[type="checkbox"]:checked');
      if (!checked.length) errors.push({ name: "categories", message: t("validation.selectCategory") });
      if (checked.length > 4) errors.push({ name: "categories", message: t("validation.categoryLimit") });
      if (categoryFieldset) categoryFieldset.setAttribute("aria-invalid", checked.length < 1 || checked.length > 4 ? "true" : "false");

      const pipelineField = form.elements.namedItem("pipeline_image_file");
      if (pipelineField?.validationMessage) {
        errors.push({ name: "pipeline_image_file", message: pipelineField.validationMessage });
      }

      return errors.filter((error, index, items) => items.findIndex((item) => item.message === error.message) === index);
    };

    const render = (errors) => {
      summary.hidden = false;
      summary.replaceChildren();
      if (!errors.length) {
        summary.dataset.state = "valid";
        const message = document.createElement("p");
        message.textContent = t("validation.passed");
        summary.append(message);
        return;
      }
      summary.dataset.state = "invalid";
      const heading = document.createElement("strong");
      heading.textContent = t("validation.heading");
      const list = document.createElement("ul");
      errors.forEach((error) => {
        const item = document.createElement("li");
        item.textContent = error.message;
        list.append(item);
      });
      summary.append(heading, list);
    };

    const validate = ({ focus = true } = {}) => {
      attempted = true;
      const errors = collectErrors();
      render(errors);
      if (errors.length && focus) {
        const first = errors[0];
        if (first.name === "categories") {
          categoryContainer.querySelector("input")?.focus();
        } else {
          form.elements.namedItem(first.name)?.focus();
        }
      }
      return errors.length === 0;
    };

    form.addEventListener("input", () => {
      if (attempted) render(collectErrors());
    });
    form.addEventListener("change", () => {
      if (attempted) render(collectErrors());
    });
    form.addEventListener("focusout", (event) => {
      if (!event.target.matches("input, textarea")) return;
      collectErrors();
    });
    window.addEventListener("sim:languagechange", () => {
      if (attempted) render(collectErrors());
    });

    const reset = () => {
      attempted = false;
      summary.hidden = true;
      delete summary.dataset.state;
      summary.replaceChildren();
      REQUIRED_FIELDS.forEach(([name]) => setFieldValidity(name, ""));
      setFieldValidity("project_url", "");
      if (categoryFieldset) categoryFieldset.removeAttribute("aria-invalid");
    };

    return { reset, validate };
  }

  window.SIMFormValidation = Object.freeze({ create });
})();
