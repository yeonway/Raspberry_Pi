(() => {
  const bootstrapEl = document.getElementById("memoBootstrap");
  if (!bootstrapEl) return;

  const AUTOSAVE_MS = 700;
  const SEARCH_MS = 250;
  const DRAFT_KEY = "memo:drafts";
  const QUEUE_KEY = "memo:retryQueue";
  const MAX_ATTACHMENTS = 5;
  const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;

  const state = {
    notes: [],
    folders: [],
    selectedId: null,
    selectedNoteIds: new Set(),
    selectedAttachmentIds: new Set(),
    selectedFolderId: "",
    trashMode: false,
    search: "",
    saveTimer: null,
    searchTimer: null,
    savingPromise: null,
    pendingSave: false,
    historyRevisions: [],
    deferredPrompt: null,
  };

  const data = JSON.parse(bootstrapEl.textContent || "{}");
  state.notes = data.notes || [];
  state.folders = data.folders || [];

  const $ = (id) => document.getElementById(id);
  const noteList = $("noteList");
  const folderList = $("folderList");
  const saveStatus = $("saveStatus");
  const noteEditor = $("noteEditor");
  const detailEmpty = $("detailEmpty");
  const historyPanel = $("historyPanel");
  const historyList = $("historyList");
  const historyModal = $("historyModal");
  const historyModalBody = $("historyModalBody");
  const attachmentInput = $("attachmentInput");
  const attachmentList = $("attachmentList");
  const attachmentError = $("attachmentError");
  const manualSaveButton = $("manualSaveButton");
  const fields = {
    title: $("noteTitle"),
    body: $("noteBody"),
    tags: $("noteTags"),
    folder: $("noteFolder"),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function setStatus(text, mode = "") {
    saveStatus.textContent = text;
    saveStatus.dataset.mode = mode;
  }

  function setSaving(isSaving) {
    if (!manualSaveButton) return;
    manualSaveButton.disabled = isSaving;
    manualSaveButton.textContent = isSaving ? "저장 중..." : "저장";
  }

  function api(path, options = {}) {
    const headers = options.headers || {};
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }
    return fetch(path, { ...options, headers }).then(async (response) => {
      if (!response.ok) {
        const text = await response.text();
        try {
          const data = JSON.parse(text);
          throw new Error(data.detail || text || response.statusText);
        } catch (error) {
          if (error instanceof SyntaxError) throw new Error(text || response.statusText);
          throw error;
        }
      }
      const contentType = response.headers.get("content-type") || "";
      return contentType.includes("application/json") ? response.json() : response.text();
    });
  }

  function readJson(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  }

  function writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function drafts() {
    return readJson(DRAFT_KEY, {});
  }

  function saveDraft(note) {
    const all = drafts();
    all[String(note.id || "new")] = {
      ...note,
      saved_at: new Date().toISOString(),
    };
    writeJson(DRAFT_KEY, all);
  }

  function clearDraft(noteId) {
    const all = drafts();
    delete all[String(noteId || "new")];
    writeJson(DRAFT_KEY, all);
  }

  function queueOperation(operation) {
    const queue = readJson(QUEUE_KEY, []);
    const duplicateIndex = queue.findIndex(
      (item) =>
        item.method === operation.method &&
        item.path === operation.path &&
        (item.body?.client_key || item.body?.id || "") === (operation.body?.client_key || operation.body?.id || ""),
    );
    if (duplicateIndex >= 0) queue.splice(duplicateIndex, 1);
    queue.push({ ...operation, queued_at: new Date().toISOString() });
    writeJson(QUEUE_KEY, queue);
  }

  async function flushQueue() {
    const queue = readJson(QUEUE_KEY, []);
    if (!queue.length || !navigator.onLine) return;
    const remaining = [];
    for (const item of queue) {
      try {
        await api(item.path, { method: item.method, body: item.body });
      } catch {
        remaining.push(item);
      }
    }
    writeJson(QUEUE_KEY, remaining);
    if (!remaining.length) {
      setStatus("온라인 동기화가 완료되었습니다", "saved");
      await refreshFolders();
      await refreshNotes();
    }
  }

  function currentNote() {
    return state.notes.find((note) => note.id === state.selectedId) || null;
  }

  function noteTitle(note) {
    return note.title || (note.body || "").split(/\r?\n/)[0] || "제목 없음";
  }

  function highlight(text) {
    const escaped = escapeHtml(text);
    const query = state.search.trim();
    if (!query) return escaped;
    const safe = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escaped.replace(new RegExp(`(${safe})`, "gi"), "<mark>$1</mark>");
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) return "0 B";
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    if (bytes >= 1024) return `${Math.ceil(bytes / 1024)} KB`;
    return `${bytes} B`;
  }

  function setAttachmentError(message = "") {
    if (!attachmentError) return;
    attachmentError.textContent = message;
    attachmentError.hidden = !message;
  }

  function validateFiles(files, existingCount = 0) {
    if (existingCount + files.length > MAX_ATTACHMENTS) {
      return `첨부는 메모 1개당 최대 ${MAX_ATTACHMENTS}개까지 가능합니다.`;
    }
    const tooLarge = files.find((file) => file.size > MAX_ATTACHMENT_BYTES);
    if (tooLarge) {
      return `${tooLarge.name} 파일이 10MB를 초과했습니다. 파일 1개당 최대 10MB까지만 첨부할 수 있습니다.`;
    }
    return "";
  }

  function sortedNotes() {
    return [...state.notes].sort((a, b) => {
      if (Number(b.pinned) !== Number(a.pinned)) return Number(b.pinned) - Number(a.pinned);
      return String(b.updated_at || "").localeCompare(String(a.updated_at || ""));
    });
  }

  function renderFolders() {
    const activeClass = state.selectedFolderId === "" && !state.trashMode ? " is-active" : "";
    const trashClass = state.trashMode ? " is-active" : "";
    folderList.innerHTML = `
      <button class="folder-item${activeClass}" type="button" data-folder-id="">전체</button>
      ${state.folders
        .map(
          (folder) => `
            <button class="folder-item${String(folder.id) === String(state.selectedFolderId) && !state.trashMode ? " is-active" : ""}" type="button" data-folder-id="${folder.id}">
              ${escapeHtml(folder.name)} <span>${folder.note_count || 0}</span>
            </button>
          `,
        )
        .join("")}
      <button class="folder-item${trashClass}" type="button" data-trash="1">휴지통</button>
    `;
    fields.folder.innerHTML = `<option value="">폴더 없음</option>${state.folders
      .map((folder) => `<option value="${folder.id}">${escapeHtml(folder.name)}</option>`)
      .join("")}`;
    const note = currentNote();
    if (note) fields.folder.value = note.folder_id || "";
  }

  function renderNotes() {
    const notes = sortedNotes();
    if (!notes.length) {
      noteList.innerHTML = `<div class="empty-state"><h2>${state.trashMode ? "휴지통이 비었습니다" : "아직 메모가 없습니다"}</h2><p>새 메모를 눌러 작성하세요.</p></div>`;
      return;
    }
    noteList.innerHTML = notes
      .map(
        (note) => `
          <article class="note-card${note.id === state.selectedId ? " is-active" : ""}" data-note-id="${note.id}">
            <label class="select-row" aria-label="메모 선택">
              <input class="note-select" type="checkbox" data-note-select="${note.id}" ${state.selectedNoteIds.has(note.id) ? "checked" : ""}>
            </label>
            <button class="note-open" type="button" data-note-open="${note.id}">
              <strong>${note.pinned ? '<span class="pin-mark">고정 </span>' : ""}${highlight(noteTitle(note))}</strong>
              <p>${highlight(note.body || "")}</p>
              <small>${highlight(note.folder_name || "폴더 없음")} · ${highlight(note.tags || "태그 없음")}${note.attachment_count ? ` · 첨부 ${note.attachment_count}` : ""}</small>
              <span>${escapeHtml(note.updated_at || "")}${note.deleted_at ? " · 휴지통" : ""}</span>
            </button>
          </article>
        `,
      )
      .join("");
  }

  function renderChecklist(note) {
    const items = note.checklist || [];
    $("checklistItems").innerHTML = items
      .map(
        (item) => `
          <div class="checklist-row" data-check-id="${escapeHtml(item.id)}">
            <input type="checkbox" ${item.checked ? "checked" : ""} aria-label="체크">
            <input type="text" value="${escapeHtml(item.text)}" aria-label="체크 항목">
            <button class="text-button" type="button">삭제</button>
          </div>
        `,
      )
      .join("");
  }

  function renderAttachments(note) {
    if (!attachmentList) return;
    const attachments = note?.attachments || [];
    if (!note) {
      attachmentList.innerHTML = "";
      return;
    }
    if (note.isNew) {
      attachmentList.innerHTML = `<p class="subtle-text">메모 저장 후 첨부할 수 있습니다.</p>`;
      return;
    }
    attachmentList.innerHTML = attachments.length
      ? attachments
          .map(
            (attachment) => `
              <div class="attachment-row" data-attachment-id="${attachment.id}">
                <input class="attachment-select" type="checkbox" data-attachment-select="${attachment.id}" ${state.selectedAttachmentIds.has(attachment.id) ? "checked" : ""} aria-label="첨부 선택">
                <a href="/api/attachments/${attachment.id}/download">${escapeHtml(attachment.filename)}</a>
                <span>${formatBytes(Number(attachment.size_bytes || 0))}</span>
                <button class="text-button" type="button" data-delete-attachment="${attachment.id}">삭제</button>
              </div>
            `,
          )
          .join("")
      : `<p class="subtle-text">첨부 파일이 없습니다.</p>`;
  }

  async function loadAttachments(note) {
    if (!note || note.isNew || note.attachmentsLoaded) return;
    try {
      const result = await api(`/api/notes/${note.id}/attachments`);
      note.attachments = result.attachments || [];
      note.attachmentsLoaded = true;
      if (note.id === state.selectedId) renderAttachments(note);
    } catch (error) {
      setAttachmentError(error.message || "첨부 목록을 불러오지 못했습니다.");
    }
  }

  function renderDetail() {
    const note = currentNote();
    if (!note) {
      noteEditor.hidden = true;
      detailEmpty.hidden = false;
      historyPanel.hidden = true;
      state.selectedAttachmentIds.clear();
      renderAttachments(null);
      return;
    }
    detailEmpty.hidden = true;
    noteEditor.hidden = false;
    fields.title.value = note.title || "";
    fields.body.value = note.body || "";
    fields.tags.value = note.tags || "";
    fields.folder.value = note.folder_id || "";
    $("pinButton").textContent = note.pinned ? "고정 해제" : "고정";
    $("trashButton").hidden = Boolean(note.deleted_at);
    $("restoreButton").hidden = !note.deleted_at;
    $("purgeButton").hidden = !note.deleted_at;
    renderChecklist(note);
    renderAttachments(note);
    loadAttachments(note);
  }

  function renderAll() {
    renderFolders();
    renderNotes();
    renderDetail();
  }

  function revealDetailOnNarrowScreen() {
    if (!window.matchMedia("(max-width: 860px)").matches) return;
    requestAnimationFrame(() => {
      document.getElementById("memoDetail")?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  }

  async function refreshNotes() {
    const params = new URLSearchParams();
    if (state.search.trim()) params.set("q", state.search.trim());
    if (state.selectedFolderId && !state.trashMode) params.set("folder_id", state.selectedFolderId);
    if (state.trashMode) params.set("trash", "true");
    const result = await api(`/api/notes?${params.toString()}`);
    state.notes = result.notes || [];
    if (state.selectedId && !state.notes.some((note) => note.id === state.selectedId)) {
      state.selectedId = state.notes[0]?.id || null;
    }
    state.selectedNoteIds = new Set([...state.selectedNoteIds].filter((id) => state.notes.some((note) => note.id === id)));
    renderAll();
  }

  async function refreshFolders() {
    const result = await api("/api/folders");
    state.folders = result.folders || [];
    renderFolders();
  }

  function collectNotePayload() {
    const note = currentNote();
    return {
      title: fields.title.value,
      body: fields.body.value,
      tags: fields.tags.value,
      folder_id: fields.folder.value || null,
      pinned: Boolean(note?.pinned),
      checklist: note?.checklist || [],
      client_key: note?.client_key || (note?.isNew ? String(note.id) : undefined),
    };
  }

  async function saveSelectedNote() {
    if (state.savingPromise) {
      state.pendingSave = true;
      return state.savingPromise;
    }
    const note = currentNote();
    if (!note) return;
    const payload = collectNotePayload();
    Object.assign(note, payload);
    saveDraft(note);
    setStatus("저장 중...", "saving");
    setSaving(true);
    state.savingPromise = (async () => {
      const result = note.isNew
        ? await api("/api/notes", { method: "POST", body: payload })
        : await api(`/api/notes/${note.id}`, { method: "PATCH", body: payload });
      const saved = result.note;
      const oldId = note.id;
      const index = state.notes.findIndex((item) => item.id === oldId);
      const previousAttachments = note.attachments || [];
      if (index >= 0) state.notes[index] = { ...saved, attachments: previousAttachments, attachmentsLoaded: note.attachmentsLoaded };
      state.selectedId = saved.id;
      if (state.selectedNoteIds.has(oldId)) {
        state.selectedNoteIds.delete(oldId);
        state.selectedNoteIds.add(saved.id);
      }
      clearDraft(oldId);
      clearDraft(saved.id);
      setStatus(navigator.onLine ? "온라인에 저장되었습니다" : "오프라인에 저장되었습니다", navigator.onLine ? "saved" : "offline");
      await refreshFolders();
      renderAll();
      return saved;
    })();
    try {
      return await state.savingPromise;
    } catch (error) {
      queueOperation({
        method: note.isNew ? "POST" : "PATCH",
        path: note.isNew ? "/api/notes" : `/api/notes/${note.id}`,
        body: payload,
      });
      setStatus("오프라인에 저장되었습니다", "offline");
      saveDraft(note);
      if (error?.message) setAttachmentError(error.message.includes("Failed to fetch") ? "" : error.message);
      return note;
    } finally {
      state.savingPromise = null;
      setSaving(false);
      if (state.pendingSave) {
        state.pendingSave = false;
        clearTimeout(state.saveTimer);
        saveSelectedNote();
      }
    }
  }

  function scheduleSave() {
    clearTimeout(state.saveTimer);
    const note = currentNote();
    if (note) {
      Object.assign(note, collectNotePayload());
      saveDraft(note);
    }
    state.saveTimer = setTimeout(saveSelectedNote, AUTOSAVE_MS);
  }

  function selectNote(noteId) {
    state.selectedId = noteId;
    state.selectedAttachmentIds.clear();
    setAttachmentError("");
    renderAll();
    revealDetailOnNarrowScreen();
  }

  function createLocalNote() {
    const tempId = `new-${Date.now()}`;
    const note = {
      id: tempId,
      client_key: tempId,
      isNew: true,
      title: "",
      body: "",
      tags: "",
      folder_id: state.selectedFolderId || null,
      folder_name: "",
      pinned: false,
      deleted_at: null,
      checklist: [],
      attachments: [],
      attachmentsLoaded: true,
      updated_at: new Date().toISOString(),
    };
    state.notes.unshift(note);
    state.selectedId = tempId;
    renderAll();
    fields.title.focus();
    revealDetailOnNarrowScreen();
    scheduleSave();
  }

  async function showHistory() {
    const note = currentNote();
    if (!note || note.isNew) return;
    const result = await api(`/api/notes/${note.id}/revisions`);
    const revisions = result.revisions || [];
    state.historyRevisions = revisions;
    historyPanel.hidden = false;
    historyList.innerHTML = revisions.length
      ? revisions
          .map(
            (revision) => `
              <article class="history-entry" data-revision-id="${revision.id}">
                <strong>${escapeHtml(revision.created_at)} · ${escapeHtml(revision.username)}</strong>
                <p>${escapeHtml(revision.summary || revision.body.slice(0, 160))}</p>
                <div class="history-actions">
                  <button class="button button-light" type="button" data-view-revision="${revision.id}">비교 보기</button>
                  <button class="button button-light" type="button" data-restore-revision="${revision.id}">이 버전 복원</button>
                </div>
              </article>
            `,
          )
          .join("")
      : `<div class="empty-state"><h2>이력이 없습니다</h2><p>수정 후 이력이 생성됩니다.</p></div>`;
  }

  function closeHistoryModal() {
    if (!historyModal) return;
    historyModal.hidden = true;
    historyModalBody.innerHTML = "";
  }

  function showRevisionCompare(revisionId) {
    const revision = state.historyRevisions.find((item) => String(item.id) === String(revisionId));
    if (!revision || !historyModal || !historyModalBody) return;
    historyModalBody.innerHTML = `
      <div class="revision-compare">
        <section>
          <h3>수정 전</h3>
          <strong>${escapeHtml(revision.before?.title || "제목 없음")}</strong>
          <pre>${escapeHtml(revision.before?.body || "")}</pre>
        </section>
        <section>
          <h3>수정 후</h3>
          <strong>${escapeHtml(revision.after?.title || "제목 없음")}</strong>
          <pre>${escapeHtml(revision.after?.body || "")}</pre>
        </section>
      </div>
    `;
    historyModal.hidden = false;
  }

  async function uploadAttachments(files) {
    const note = currentNote();
    if (!note || !files.length) return;
    setAttachmentError("");
    if (note.isNew) await saveSelectedNote();
    const savedNote = currentNote();
    if (!savedNote || savedNote.isNew) {
      setAttachmentError("오프라인 상태에서는 새 메모를 먼저 온라인 저장한 뒤 첨부할 수 있습니다.");
      return;
    }
    const attachments = savedNote.attachments || [];
    const validation = validateFiles(files, attachments.length);
    if (validation) {
      setAttachmentError(validation);
      return;
    }
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    setStatus("첨부 저장 중...", "saving");
    try {
      const result = await api(`/api/notes/${savedNote.id}/attachments`, { method: "POST", body: form });
      savedNote.attachments = [...attachments, ...(result.attachments || [])];
      savedNote.attachmentsLoaded = true;
      savedNote.attachment_count = savedNote.attachments.length;
      setStatus("첨부가 저장되었습니다", "saved");
      renderAll();
    } catch (error) {
      setAttachmentError(error.message || "첨부 저장에 실패했습니다.");
      setStatus("첨부 저장 실패", "error");
    }
  }

  async function deleteAttachmentIds(ids) {
    const note = currentNote();
    if (!note || !ids.length) return;
    if (ids.length > 1 && !window.confirm(`첨부 ${ids.length}개를 삭제할까요?`)) return;
    for (const id of ids) {
      await api(`/api/attachments/${id}`, { method: "DELETE" });
    }
    note.attachments = (note.attachments || []).filter((attachment) => !ids.includes(attachment.id));
    note.attachment_count = note.attachments.length;
    ids.forEach((id) => state.selectedAttachmentIds.delete(id));
    setStatus("첨부가 삭제되었습니다", "saved");
    renderAll();
  }

  async function deleteSelectedNotes() {
    const ids = [...state.selectedNoteIds];
    if (!ids.length && state.selectedId) ids.push(state.selectedId);
    if (!ids.length) return;
    if (ids.length > 1 && !window.confirm(`메모 ${ids.length}개를 삭제할까요?`)) return;
    for (const id of ids) {
      const note = state.notes.find((item) => item.id === id);
      if (!note || note.isNew) continue;
      await api(state.trashMode ? `/api/notes/${id}` : `/api/notes/${id}/trash`, { method: state.trashMode ? "DELETE" : "POST" });
    }
    state.selectedNoteIds.clear();
    state.selectedId = null;
    await refreshNotes();
    setStatus(state.trashMode ? "메모가 영구 삭제되었습니다" : "메모가 휴지통으로 이동했습니다", "saved");
  }

  function registerPwa() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      state.deferredPrompt = event;
      $("installAppButton").hidden = false;
    });
  }

  function bindEvents() {
    $("newNoteButton").addEventListener("click", createLocalNote);
    $("manualSaveButton").addEventListener("click", () => {
      clearTimeout(state.saveTimer);
      saveSelectedNote();
    });
    $("installAppButton").addEventListener("click", async () => {
      if (!state.deferredPrompt) return;
      state.deferredPrompt.prompt();
      await state.deferredPrompt.userChoice;
      state.deferredPrompt = null;
      $("installAppButton").hidden = true;
    });

    $("searchInput").addEventListener("input", (event) => {
      state.search = event.target.value;
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(refreshNotes, SEARCH_MS);
    });

    folderList.addEventListener("click", async (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      state.trashMode = button.dataset.trash === "1";
      state.selectedFolderId = button.dataset.folderId || "";
      $("showTrashButton").hidden = state.trashMode;
      $("showActiveButton").hidden = !state.trashMode;
      await refreshNotes();
    });

    $("showTrashButton").addEventListener("click", async () => {
      state.trashMode = true;
      state.selectedFolderId = "";
      $("showTrashButton").hidden = true;
      $("showActiveButton").hidden = false;
      await refreshNotes();
    });
    $("showActiveButton").addEventListener("click", async () => {
      state.trashMode = false;
      $("showTrashButton").hidden = false;
      $("showActiveButton").hidden = true;
      await refreshNotes();
    });

    $("folderCreateForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = event.currentTarget.elements.name;
      if (!input.value.trim()) return;
      await api("/api/folders", { method: "POST", body: { name: input.value.trim() } });
      input.value = "";
      await refreshFolders();
    });

    $("renameFolderButton").addEventListener("click", async () => {
      if (!state.selectedFolderId) return;
      const folder = state.folders.find((item) => String(item.id) === String(state.selectedFolderId));
      const name = window.prompt("새 폴더 이름", folder?.name || "");
      if (!name) return;
      await api(`/api/folders/${state.selectedFolderId}`, { method: "PATCH", body: { name } });
      await refreshFolders();
    });

    $("deleteFolderButton").addEventListener("click", async () => {
      if (!state.selectedFolderId) return;
      if (!window.confirm("폴더를 삭제하고 메모는 폴더 없음으로 이동할까요?")) return;
      await api(`/api/folders/${state.selectedFolderId}`, { method: "DELETE" });
      state.selectedFolderId = "";
      await refreshFolders();
      await refreshNotes();
    });

    noteList.addEventListener("change", (event) => {
      const checkbox = event.target.closest("[data-note-select]");
      if (!checkbox) return;
      const id = Number(checkbox.dataset.noteSelect) || checkbox.dataset.noteSelect;
      if (checkbox.checked) state.selectedNoteIds.add(id);
      else state.selectedNoteIds.delete(id);
    });

    noteList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-note-open]");
      if (!button) return;
      const id = Number(button.dataset.noteOpen) || button.dataset.noteOpen;
      selectNote(id);
    });

    [fields.title, fields.body, fields.tags, fields.folder].forEach((field) => {
      field.addEventListener("input", scheduleSave);
      field.addEventListener("change", scheduleSave);
    });

    $("pinButton").addEventListener("click", () => {
      const note = currentNote();
      if (!note) return;
      note.pinned = !note.pinned;
      renderAll();
      scheduleSave();
    });

    $("trashButton").addEventListener("click", async () => {
      const note = currentNote();
      if (!note || note.isNew) return;
      await api(`/api/notes/${note.id}/trash`, { method: "POST" });
      state.selectedId = null;
      await refreshNotes();
    });

    $("restoreButton").addEventListener("click", async () => {
      const note = currentNote();
      if (!note) return;
      await api(`/api/notes/${note.id}/restore`, { method: "POST" });
      state.trashMode = false;
      $("showTrashButton").hidden = false;
      $("showActiveButton").hidden = true;
      await refreshNotes();
    });

    $("purgeButton").addEventListener("click", async () => {
      const note = currentNote();
      if (!note || !window.confirm("영구 삭제할까요?")) return;
      await api(`/api/notes/${note.id}`, { method: "DELETE" });
      state.selectedId = null;
      await refreshNotes();
    });

    $("addChecklistItemButton").addEventListener("click", () => {
      const input = $("checklistInput");
      const note = currentNote();
      if (!note || !input.value.trim()) return;
      note.checklist = note.checklist || [];
      note.checklist.push({ id: `item-${Date.now()}`, text: input.value.trim(), checked: false });
      input.value = "";
      renderChecklist(note);
      scheduleSave();
    });

    $("checklistItems").addEventListener("input", (event) => {
      const row = event.target.closest(".checklist-row");
      const note = currentNote();
      if (!row || !note) return;
      const item = note.checklist.find((entry) => entry.id === row.dataset.checkId);
      if (!item) return;
      item.text = row.querySelector('input[type="text"]').value;
      item.checked = row.querySelector('input[type="checkbox"]').checked;
      scheduleSave();
    });

    $("checklistItems").addEventListener("change", (event) => {
      if (!event.target.matches('input[type="checkbox"]')) return;
      const row = event.target.closest(".checklist-row");
      const note = currentNote();
      if (!row || !note) return;
      const item = note.checklist.find((entry) => entry.id === row.dataset.checkId);
      if (!item) return;
      item.checked = event.target.checked;
      scheduleSave();
    });

    $("checklistItems").addEventListener("click", (event) => {
      const remove = event.target.closest("button");
      const row = event.target.closest(".checklist-row");
      const note = currentNote();
      if (!remove || !row || !note) return;
      note.checklist = note.checklist.filter((item) => item.id !== row.dataset.checkId);
      renderChecklist(note);
      scheduleSave();
    });

    attachmentInput?.addEventListener("change", async (event) => {
      const files = [...event.target.files];
      event.target.value = "";
      await uploadAttachments(files);
    });

    attachmentList?.addEventListener("change", (event) => {
      const checkbox = event.target.closest("[data-attachment-select]");
      if (!checkbox) return;
      const id = Number(checkbox.dataset.attachmentSelect);
      if (checkbox.checked) state.selectedAttachmentIds.add(id);
      else state.selectedAttachmentIds.delete(id);
    });

    attachmentList?.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-delete-attachment]");
      if (!button) return;
      await deleteAttachmentIds([Number(button.dataset.deleteAttachment)]);
    });

    $("historyButton").addEventListener("click", showHistory);
    $("closeHistoryButton").addEventListener("click", () => {
      historyPanel.hidden = true;
    });
    $("historyModalClose")?.addEventListener("click", closeHistoryModal);
    historyModal?.addEventListener("click", (event) => {
      if (event.target === historyModal) closeHistoryModal();
    });
    historyList.addEventListener("click", async (event) => {
      const button = event.target.closest("button");
      const entry = event.target.closest("[data-revision-id]");
      const note = currentNote();
      if (!button || !entry || !note) return;
      if (button.dataset.viewRevision) {
        showRevisionCompare(button.dataset.viewRevision);
        return;
      }
      const result = await api(`/api/notes/${note.id}/revisions/${entry.dataset.revisionId}/restore`, { method: "POST" });
      const index = state.notes.findIndex((item) => item.id === note.id);
      if (index >= 0) state.notes[index] = result.note;
      renderAll();
      await showHistory();
    });

    window.addEventListener("online", flushQueue);
    document.addEventListener("keydown", async (event) => {
      const active = document.activeElement;
      const isTyping = active?.matches?.("input, textarea, select, [contenteditable='true']");
      if (event.key !== "Delete" || isTyping) return;
      if (state.selectedAttachmentIds.size) {
        event.preventDefault();
        await deleteAttachmentIds([...state.selectedAttachmentIds]);
        return;
      }
      if (state.selectedNoteIds.size || state.selectedId) {
        event.preventDefault();
        await deleteSelectedNotes();
      }
    });
  }

  registerPwa();
  bindEvents();
  renderAll();
  flushQueue();
})();
