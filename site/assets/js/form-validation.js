(() => {
  "use strict";

  const t = (key, values) => window.SIMI18n.t(key, values);
  const DATE_PATTERN = /^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$/;
  const REQUIRED_FIELDS = [
    ["title", "validation.titleRequired"],
    ["date", "validation.dateRequired"],
    ["paper_url", "validation.paperUrlRequired"],
    ["authors", "validation.authorsRequired"],
    ["abstract", "validation.abstractRequired"],
  ];
  const REQUIRED_MESSAGES = new Map(REQUIRED_FIELDS);
  const VALIDATED_FIELDS = new Set(REQUIRED_MESSAGES.keys());

  const fieldValue = (form, name) => String(form.elements.namedItem(name)?.value || "").trim();

  function create({ form, categoryContainer, summary }) {
    if (!form || !summary) return null;
    let attempted = false;

    const setFieldValidity = (name, message) => {
      const field = form.elements.namedItem(name);
      if (!field || typeof field.setCustomValidity !== "function") return;
      field.setCustomValidity(message || "");
      field.setAttribute("aria-invalid", message ? "true" : "false");
    };

    const fieldError = (name) => {
      const value = fieldValue(form, name);
      const requiredMessage = REQUIRED_MESSAGES.get(name);
      if (requiredMessage && !value) return t(requiredMessage);

      if (name === "date") return value && !DATE_PATTERN.test(value) ? t("validation.dateFormat") : "";
      if (name === "paper_url" && value && !/^https?:\/\/\S+$/i.test(value)) {
        return t("validation.urlFormat", {
          label: t("validation.paperUrl"),
        });
      }
      return "";
    };

    const collectErrors = () => {
      const errors = [];
      VALIDATED_FIELDS.forEach((name) => {
        const message = fieldError(name);
        setFieldValidity(name, message);
        if (message) errors.push({ name, message });
      });

      const pipelineField = form.elements.namedItem("pipeline_image_file");
      if (pipelineField?.validationMessage) {
        errors.push({ name: "pipeline_image_file", message: pipelineField.validationMessage });
      }
      const paperFileField = form.elements.namedItem("paper_file_upload");
      if (paperFileField?.validationMessage) {
        errors.push({ name: "paper_file_upload", message: paperFileField.validationMessage });
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
        form.elements.namedItem(first.name)?.focus();
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
      const name = event.target.name;
      if (VALIDATED_FIELDS.has(name)) setFieldValidity(name, fieldError(name));
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
    };

    return { reset, validate };
  }

  window.SIMFormValidation = Object.freeze({ create });
})();
