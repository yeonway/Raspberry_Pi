document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "진행할까요?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.querySelector(button.getAttribute("data-toggle"));
      if (target) {
        target.hidden = !target.hidden;
      }
    });
  });

  document.querySelectorAll("[data-menu-button]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const popover = button.parentElement ? button.parentElement.querySelector(".community-menu-popover") : null;
      document.querySelectorAll(".community-menu-popover").forEach((item) => {
        if (item !== popover) item.hidden = true;
      });
      if (popover) popover.hidden = !popover.hidden;
    });
  });

  document.addEventListener("click", () => {
    document.querySelectorAll(".community-menu-popover").forEach((item) => {
      item.hidden = true;
    });
  });

  document.querySelectorAll("[data-modal-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.querySelector(button.getAttribute("data-modal-open"));
      if (modal) modal.hidden = false;
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = button.closest(".community-modal");
      if (modal) modal.hidden = true;
    });
  });

  document.querySelectorAll(".community-modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) modal.hidden = true;
    });
  });

  document.querySelectorAll("[data-copy-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.getAttribute("data-copy-url") || window.location.href;
      try {
        await navigator.clipboard.writeText(value);
        button.textContent = "복사됨";
      } catch (_) {
        window.prompt("링크를 복사하세요.", value);
      }
    });
  });

  document.querySelectorAll("[data-counter]").forEach((field) => {
    const wrapper = field.closest("label") || field.parentElement;
    const counter = wrapper ? wrapper.querySelector("[data-count]") : null;
    const update = () => {
      if (counter) {
        counter.textContent = String(field.value.length);
      }
    };
    field.addEventListener("input", update);
    update();
  });
});
