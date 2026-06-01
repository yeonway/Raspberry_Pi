const storageKey = "useless-lab-state";

const defaultState = {
  reactionBest: null,
  reactionCount: 0,
  clickBest: 0,
  rps: { win: 0, draw: 0, lose: 0 },
  records: [],
};

let state = loadState();
let activeGame = "reaction";
let reactionTimer = null;
let reactionStartedAt = 0;
let reactionStatus = "idle";
let clickTimer = null;
let clickEndAt = 0;
let clickRunning = false;
let clickCount = 0;
let baseballAnswer = makeBaseballAnswer();
let drawing = false;
let brushColor = "#111111";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const panels = $$("[data-panel]");
const tabs = $$(".game-tab");
const recordList = $("[data-record-list]");

function loadState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey));
    return { ...defaultState, ...parsed, rps: { ...defaultState.rps, ...parsed?.rps } };
  } catch {
    return structuredClone(defaultState);
  }
}

function saveState() {
  localStorage.setItem(storageKey, JSON.stringify(state));
}

function addRecord(label, value) {
  const now = new Date();
  state.records.unshift({
    label,
    value,
    time: `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`,
  });
  state.records = state.records.slice(0, 6);
  saveState();
  renderRecords();
}

function renderRecords() {
  const records = state.records.length
    ? state.records
    : [
        { label: "반응속도", value: "아직 없음", time: "--:--" },
        { label: "순간 클릭", value: "아직 없음", time: "--:--" },
        { label: "가위바위보", value: "아직 없음", time: "--:--" },
      ];

  recordList.innerHTML = records
    .map((record) => `<li><span>${record.label}</span><strong>${record.value}</strong><small>${record.time}</small></li>`)
    .join("");
}

function switchGame(game) {
  activeGame = game;
  tabs.forEach((tab) => {
    const selected = tab.dataset.game === game;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });
  panels.forEach((panel) => {
    const selected = panel.dataset.panel === game;
    panel.classList.toggle("is-active", selected);
    panel.hidden = !selected;
  });
  location.hash = game;
}

function updateReactionStats() {
  $("[data-reaction-best]").textContent = state.reactionBest ? `${state.reactionBest.toFixed(3)}초` : "없음";
  $("[data-reaction-count]").textContent = `${state.reactionCount}회`;
}

function resetReactionPad(text, className = "") {
  const pad = $("[data-reaction-pad]");
  pad.className = `reaction-pad ${className}`.trim();
  pad.textContent = text;
}

function startReaction() {
  clearTimeout(reactionTimer);
  reactionStatus = "waiting";
  $("[data-reaction-time]").textContent = "대기 중";
  resetReactionPad("아직 누르지 마!", "is-waiting");
  const delay = 1200 + Math.random() * 2600;
  reactionTimer = setTimeout(() => {
    reactionStatus = "ready";
    reactionStartedAt = performance.now();
    resetReactionPad("지금 클릭!", "is-ready");
  }, delay);
}

function handleReactionClick() {
  if (reactionStatus === "idle") {
    startReaction();
    return;
  }
  if (reactionStatus === "waiting") {
    clearTimeout(reactionTimer);
    reactionStatus = "idle";
    $("[data-reaction-time]").textContent = "너무 빨랐음";
    resetReactionPad("성급했다. 다시 시작!", "is-done");
    return;
  }
  if (reactionStatus !== "ready") return;

  const seconds = (performance.now() - reactionStartedAt) / 1000;
  reactionStatus = "idle";
  state.reactionCount += 1;
  if (!state.reactionBest || seconds < state.reactionBest) {
    state.reactionBest = seconds;
  }
  $("[data-reaction-time]").textContent = `${seconds.toFixed(3)}초`;
  resetReactionPad(`${seconds.toFixed(3)}초`, "is-done");
  addRecord("반응속도", `${seconds.toFixed(3)}초`);
  updateReactionStats();
  saveState();
}

function updateClickStats(remaining = 10) {
  $("[data-click-time]").textContent = `${remaining.toFixed(1)}초`;
  $("[data-click-count]").textContent = `${clickCount}회`;
  $("[data-click-best]").textContent = `${state.clickBest}회`;
}

function startClicker() {
  clearInterval(clickTimer);
  clickRunning = true;
  clickCount = 0;
  clickEndAt = performance.now() + 10000;
  $("[data-click-pad]").textContent = "눌러!";
  updateClickStats(10);
  clickTimer = setInterval(() => {
    const remaining = Math.max(0, (clickEndAt - performance.now()) / 1000);
    updateClickStats(remaining);
    if (remaining <= 0) finishClicker();
  }, 80);
}

function finishClicker() {
  if (!clickRunning) return;
  clickRunning = false;
  clearInterval(clickTimer);
  $("[data-click-pad]").textContent = `${clickCount}회`;
  if (clickCount > state.clickBest) state.clickBest = clickCount;
  addRecord("순간 클릭", `${clickCount}회`);
  updateClickStats(0);
  saveState();
}

function handleClickPad() {
  if (!clickRunning) {
    startClicker();
    return;
  }
  clickCount += 1;
  $("[data-click-count]").textContent = `${clickCount}회`;
}

function playRps(userChoice) {
  const choices = ["가위", "바위", "보"];
  const computer = choices[Math.floor(Math.random() * choices.length)];
  const wins =
    (userChoice === "가위" && computer === "보") ||
    (userChoice === "바위" && computer === "가위") ||
    (userChoice === "보" && computer === "바위");

  let result = "무승부";
  if (userChoice === computer) {
    state.rps.draw += 1;
  } else if (wins) {
    state.rps.win += 1;
    result = "승리";
  } else {
    state.rps.lose += 1;
    result = "패배";
  }

  $("[data-rps-result]").textContent = `나: ${userChoice} / 컴퓨터: ${computer} / ${result}`;
  addRecord("가위바위보", result);
  renderRps();
  saveState();
}

function renderRps() {
  $("[data-rps-win]").textContent = state.rps.win;
  $("[data-rps-draw]").textContent = state.rps.draw;
  $("[data-rps-lose]").textContent = state.rps.lose;
}

function makeBaseballAnswer() {
  const digits = [];
  while (digits.length < 3) {
    const digit = String(Math.floor(Math.random() * 10));
    if (!digits.includes(digit)) digits.push(digit);
  }
  return digits.join("");
}

function validateGuess(guess) {
  if (!/^\d{3}$/.test(guess)) return "숫자 3개를 입력해.";
  if (new Set(guess).size !== 3) return "중복 없는 숫자로 다시.";
  return "";
}

function scoreBaseball(guess) {
  let strike = 0;
  let ball = 0;
  guess.split("").forEach((digit, index) => {
    if (baseballAnswer[index] === digit) strike += 1;
    else if (baseballAnswer.includes(digit)) ball += 1;
  });
  return { strike, ball };
}

function submitBaseball(event) {
  event.preventDefault();
  const input = $("#guess-input");
  const guess = input.value.trim();
  const error = validateGuess(guess);
  if (error) {
    $("[data-baseball-message]").textContent = error;
    return;
  }

  const { strike, ball } = scoreBaseball(guess);
  const list = $("[data-guess-list]");
  const item = document.createElement("li");
  item.innerHTML = `<span>${guess}</span><strong>${strike}S ${ball}B</strong>`;
  list.prepend(item);
  input.value = "";

  if (strike === 3) {
    const tries = list.children.length;
    $("[data-baseball-message]").textContent = `${tries}번 만에 정답! 새 문제로 넘어가자.`;
    addRecord("숫자 야구", `${tries}번 성공`);
  } else if (strike === 0 && ball === 0) {
    $("[data-baseball-message]").textContent = "아웃. 하나도 안 맞음.";
  } else {
    $("[data-baseball-message]").textContent = `${strike} 스트라이크, ${ball} 볼`;
  }
}

function resetBaseball() {
  baseballAnswer = makeBaseballAnswer();
  $("[data-guess-list]").innerHTML = "";
  $("[data-baseball-message]").textContent = "새 문제 생성 완료.";
  $("#guess-input").value = "";
}

function setupDoodle() {
  const canvas = $("[data-doodle-canvas]");
  const ctx = canvas.getContext("2d");
  let last = null;

  function point(event) {
    const rect = canvas.getBoundingClientRect();
    const pointer = event.touches?.[0] ?? event;
    return {
      x: ((pointer.clientX - rect.left) / rect.width) * canvas.width,
      y: ((pointer.clientY - rect.top) / rect.height) * canvas.height,
    };
  }

  function draw(event) {
    if (!drawing) return;
    event.preventDefault();
    const next = point(event);
    ctx.strokeStyle = brushColor;
    ctx.lineWidth = Number($("[data-brush-size]").value);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(next.x, next.y);
    ctx.stroke();
    last = next;
  }

  canvas.addEventListener("pointerdown", (event) => {
    drawing = true;
    last = point(event);
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", draw);
  canvas.addEventListener("pointerup", () => {
    drawing = false;
    addRecord("낙서판", "낙서함");
  });
  canvas.addEventListener("pointercancel", () => {
    drawing = false;
  });
  $("[data-doodle-clear]").addEventListener("click", () => ctx.clearRect(0, 0, canvas.width, canvas.height));
}

function bindEvents() {
  tabs.forEach((tab) => tab.addEventListener("click", () => switchGame(tab.dataset.game)));
  $("[data-reaction-start]").addEventListener("click", startReaction);
  $("[data-reaction-pad]").addEventListener("click", handleReactionClick);
  $("[data-click-start]").addEventListener("click", startClicker);
  $("[data-click-pad]").addEventListener("click", handleClickPad);
  $$("[data-rps]").forEach((button) => button.addEventListener("click", () => playRps(button.dataset.rps)));
  $("[data-baseball-form]").addEventListener("submit", submitBaseball);
  $("[data-baseball-reset]").addEventListener("click", resetBaseball);
  $$("[data-color]").forEach((button) => {
    button.addEventListener("click", () => {
      brushColor = button.dataset.color;
      $$("[data-color]").forEach((item) => item.classList.toggle("is-active", item === button));
    });
  });
  $$("[data-action]").forEach((button) => {
    button.addEventListener("click", () => handleAction(button.dataset.action));
  });
}

function handleAction(action) {
  if (action === "random-game") {
    const games = ["reaction", "clicker", "rps", "baseball", "doodle"];
    switchGame(games[Math.floor(Math.random() * games.length)]);
  }
  if (action === "reset-all" && confirm("기록을 전부 지울까?")) {
    state = structuredClone(defaultState);
    saveState();
    renderAll();
  }
  if (action === "show-records") {
    document.querySelector(".record-board").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  if (action === "add-memo") {
    addRecord("아이디어", "메모 추가");
  }
}

function renderAll() {
  renderRecords();
  updateReactionStats();
  clickCount = 0;
  updateClickStats(10);
  renderRps();
}

function init() {
  bindEvents();
  setupDoodle();
  renderAll();
  const hashGame = location.hash.replace("#", "");
  if (["reaction", "clicker", "rps", "baseball", "doodle"].includes(hashGame)) {
    switchGame(hashGame);
  }
}

init();
