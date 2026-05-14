document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "진행할까요?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  const titleInput = document.querySelector("[data-preview-title]");
  const slugInput = document.querySelector("[data-preview-slug]");
  const categoryInput = document.querySelector("[data-preview-category]");
  const summaryInput = document.querySelector("[data-preview-summary]");
  const contentInput = document.querySelector("[data-preview-content]");

  const titleOutput = document.querySelector("[data-preview-title-output]");
  const slugOutput = document.querySelector("[data-preview-slug-output]");
  const categoryOutput = document.querySelector("[data-preview-category-output]");
  const summaryOutput = document.querySelector("[data-preview-summary-output]");
  const contentOutput = document.querySelector("[data-preview-content-output]");
  const previewPanel = document.querySelector(".preview-panel");
  const previewToggle = document.querySelector("#previewToggle");

  if (!titleInput || !slugInput) {
    return;
  }

  let slugTouched = Boolean(slugInput.value.trim());

  const slugify = (value) => {
    const slug = value
      .normalize("NFKD")
      .replace(/[^\x00-\x7F]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");
    return slug || "news";
  };

  const excerpt = (value) => {
    const clean = value.replace(/[#>*_`~[\]()]/g, " ").replace(/\s+/g, " ").trim();
    if (!clean) {
      return "요약이 비어 있으면 본문에서 자동 생성됩니다.";
    }
    return clean.length > 170 ? `${clean.slice(0, 169).trim()}...` : clean;
  };

  const updatePreview = () => {
    if (!slugTouched && titleInput.value.trim()) {
      slugInput.value = slugify(titleInput.value);
    }
    if (titleOutput) {
      titleOutput.textContent = titleInput.value.trim() || "제목 없음";
    }
    if (slugOutput) {
      slugOutput.textContent = slugInput.value.trim() || "자동 생성";
    }
    if (categoryOutput && categoryInput) {
      categoryOutput.textContent = categoryInput.value || "general";
    }
    if (summaryOutput && summaryInput && contentInput) {
      summaryOutput.textContent = summaryInput.value.trim() || excerpt(contentInput.value);
    }
    if (contentOutput && contentInput) {
      contentOutput.textContent = contentInput.value.trim().slice(0, 420) || "본문 미리보기";
    }
  };

  slugInput.addEventListener("input", () => {
    slugTouched = Boolean(slugInput.value.trim());
    updatePreview();
  });

  [titleInput, categoryInput, summaryInput, contentInput].forEach((element) => {
    if (element) {
      element.addEventListener("input", updatePreview);
      element.addEventListener("change", updatePreview);
    }
  });

  if (previewToggle && previewPanel) {
    previewToggle.addEventListener("click", () => {
      previewPanel.classList.toggle("is-open");
      previewPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  updatePreview();
});
