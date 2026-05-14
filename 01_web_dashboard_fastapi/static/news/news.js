(() => {
  const FONT_STORAGE_KEY = "dcoutNewsFontSize";

  const showToast = (message) => {
    const toast = document.querySelector("[data-toast]");
    if (!toast) {
      return;
    }
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 2200);
  };

  const copyText = async (value) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  };

  const applyFontSize = (size) => {
    const articleBody = document.querySelector("[data-article-body]");
    if (!articleBody) {
      return;
    }
    articleBody.classList.remove("is-small", "is-large");
    if (size === "small") {
      articleBody.classList.add("is-small");
    }
    if (size === "large") {
      articleBody.classList.add("is-large");
    }
    localStorage.setItem(FONT_STORAGE_KEY, size);
  };

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
    const clean = value.replace(/[#>*_`~[\]()|]/g, " ").replace(/\s+/g, " ").trim();
    if (!clean) {
      return "요약이 비어 있으면 본문에서 자동 생성됩니다.";
    }
    return clean.length > 170 ? `${clean.slice(0, 169).trim()}...` : clean;
  };

  const initAdminPreview = () => {
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

    if (!titleInput || !slugInput) {
      return;
    }

    let slugTouched = Boolean(slugInput.value.trim());

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
        const selected = categoryInput.options[categoryInput.selectedIndex];
        categoryOutput.textContent = selected ? selected.textContent.trim() : categoryInput.value;
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

    updatePreview();
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        const message = form.getAttribute("data-confirm") || "진행할까요?";
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });

    const savedFontSize = localStorage.getItem(FONT_STORAGE_KEY);
    if (savedFontSize) {
      applyFontSize(savedFontSize);
    }

    document.querySelectorAll("[data-copy-url]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await copyText(window.location.href);
          showToast("주소를 복사했습니다.");
        } catch {
          showToast("주소 복사에 실패했습니다.");
        }
      });
    });

    document.querySelectorAll("[data-share-url]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (navigator.share) {
          try {
            await navigator.share({ title: document.title, url: window.location.href });
            return;
          } catch (error) {
            if (error && error.name === "AbortError") {
              return;
            }
          }
        }

        try {
          await copyText(window.location.href);
          showToast("공유 주소를 복사했습니다.");
        } catch {
          showToast("공유를 준비하지 못했습니다.");
        }
      });
    });

    document.querySelectorAll("[data-font-size]").forEach((button) => {
      button.addEventListener("click", () => {
        applyFontSize(button.getAttribute("data-font-size") || "normal");
      });
    });

    document.querySelectorAll("[data-print]").forEach((button) => {
      button.addEventListener("click", () => window.print());
    });

    document.querySelectorAll("[data-comment-counter]").forEach((textarea) => {
      const counter = document.querySelector("[data-comment-count]");
      const updateCounter = () => {
        if (counter) {
          counter.textContent = String(textarea.value.length);
        }
      };
      textarea.addEventListener("input", updateCounter);
      updateCounter();
    });

    initAdminPreview();
  });
})();
