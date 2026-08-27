(() => {
  "use strict";

  async function initializeImageSlots() {
    const slots = [...document.querySelectorAll("[data-image-slot]")];
    if (!slots.length || !window.SIMSite) return;
    try {
      const response = await fetch("./assets/data/image-slots.json", { cache: "no-cache" });
      if (!response.ok) return;
      const data = await response.json();
      slots.forEach((slot) => {
        const config = data.slots?.[slot.dataset.imageSlot];
        if (!config || !window.SIMSite.isSafeImageUrl(config.src)) return;
        const image = slot.querySelector("img");
        const caption = slot.querySelector("figcaption");
        image.src = config.src;
        image.alt = String(config.alt || "").trim();
        if (caption) {
          caption.textContent = String(config.caption || "").trim();
          caption.hidden = !caption.textContent;
        }
        slot.hidden = false;
      });
    } catch (_error) {
      // Optional image slots remain hidden when their configuration is unavailable.
    }
  }

  initializeImageSlots();
})();
