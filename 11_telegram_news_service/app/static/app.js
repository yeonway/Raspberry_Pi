async function postJson(url) {
  const response = await fetch(url, { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

function renderResult(target, value) {
  const element = document.querySelector(target);
  if (element) {
    element.textContent = JSON.stringify(value, null, 2);
  }
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  button.disabled = true;
  const previousText = button.textContent;
  button.textContent = "실행 중";
  try {
    if (action === "phone-health") {
      renderResult("#phone-health-result", await getJson("/admin/phone-health"));
    } else if (action === "collect") {
      renderResult("#manual-result", await postJson("/admin/collect-once"));
    } else if (action === "score") {
      renderResult("#manual-result", await postJson("/admin/score-once"));
    } else if (action === "digest") {
      renderResult("#manual-result", await postJson("/admin/send-digest-once"));
    }
  } catch (error) {
    renderResult(action === "phone-health" ? "#phone-health-result" : "#manual-result", { error: error.message });
  } finally {
    button.disabled = false;
    button.textContent = previousText;
  }
});
