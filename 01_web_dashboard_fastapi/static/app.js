const $ = (id) => document.getElementById(id);
let refreshTimer = null;

function setText(id, value) {
  $(id).textContent = value ?? "-";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (res.status === 401) {
    showLogin();
    throw new Error("로그인이 필요합니다.");
  }

  if (!res.ok) {
    throw new Error(`API 오류: ${res.status}`);
  }

  return await res.json();
}

function serviceLabel(value) {
  if (value === "running") return "실행 중";
  if (value === "stopped") return "중지";
  if (value === "start_requested") return "시작 요청됨";
  if (value === "stop_requested") return "중지 요청됨";
  if (value === "restart_requested") return "재시작 요청됨";
  return value || "-";
}

function showLogin(message = "") {
  $("loginView").classList.remove("hidden");
  $("dashboardView").classList.add("hidden");
  $("loginMessage").textContent = message;

  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

function showDashboard(username) {
  $("loginView").classList.add("hidden");
  $("dashboardView").classList.remove("hidden");
  setText("currentUser", `login: ${username}`);

  if (!refreshTimer) {
    refreshTimer = setInterval(refreshAll, 3000);
  }
}

async function checkAuth() {
  const data = await api("/api/auth/me");

  if (data.authenticated) {
    showDashboard(data.username);
    await refreshAll();
  } else {
    showLogin();
  }
}

async function login(username, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  if (!data.ok) {
    showLogin(data.message || "로그인 실패");
    return;
  }

  showDashboard(data.username);
  await refreshAll();
}

async function logout() {
  await api("/api/auth/logout", { method: "POST" });
  showLogin("로그아웃 완료");
}

async function refreshStatus() {
  const data = await api("/api/status");

  const system = data.system;
  const services = data.services;

  setText("cpu", `${system.cpu_percent}%`);
  setText("ram", `${system.ram_percent}% (${system.ram_used_mb}MB / ${system.ram_total_mb}MB)`);
  setText("temp", system.temperature_c === null ? "PC 테스트 중" : `${system.temperature_c}°C`);
  setText("disk", system.disk_percent === null ? "-" : `${system.disk_percent}%`);
  setText("os", system.os);

  setText("minecraftState", serviceLabel(services.minecraft_server));
  setText("backupState", services.last_backup_request || "-");
}

async function refreshLogs() {
  const data = await api("/api/logs?lines=120");
  $("logs").textContent = data.logs.length ? data.logs.join("") : "로그 없음";
}

async function refreshEvents() {
  const data = await api("/api/events");
  $("events").textContent = JSON.stringify(data.events.slice(-5), null, 2);
}

async function refreshAll() {
  try {
    await refreshStatus();
    await refreshLogs();
    await refreshEvents();
  } catch (err) {
    $("commandResult").textContent = err.message;
  }
}

async function sendCommand(command) {
  try {
    const data = await api("/api/command", {
      method: "POST",
      body: JSON.stringify({ command }),
    });

    $("commandResult").textContent = data.message;
    await refreshAll();
  } catch (err) {
    $("commandResult").textContent = err.message;
  }
}

document.querySelectorAll("button[data-command]").forEach((btn) => {
  btn.addEventListener("click", () => {
    sendCommand(btn.dataset.command);
  });
});

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = $("username").value.trim();
  const password = $("password").value;

  if (!username || !password) {
    showLogin("아이디와 비밀번호를 입력하세요.");
    return;
  }

  await login(username, password);
});

$("logoutBtn").addEventListener("click", logout);
$("refreshBtn").addEventListener("click", refreshAll);

$("sendEventBtn").addEventListener("click", async () => {
  const text = $("eventText").value.trim();

  if (!text) return;

  await api("/api/event", {
    method: "POST",
    body: JSON.stringify({
      type: "manual_test",
      message: text,
    }),
  });

  $("eventText").value = "";
  await refreshAll();
});

checkAuth();
