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
