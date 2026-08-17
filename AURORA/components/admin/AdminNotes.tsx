"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  StickyNote,
  Search,
  Archive,
  Trash2,
  Plus,
  X,
  GripHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Note {
  id: string;
  title: string;
  content: string;
  linkContext?: string;
  createdAt: string;
  archived: boolean;
}

function useNotes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/config");
      const data = await res.json();
      setNotes(data.notes || []);
    } catch {
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const saveNote = useCallback(
    async (note: Partial<Note> & { id?: string }) => {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "saveNote", note }),
      });
      refetch();
    },
    [refetch]
  );

  const deleteNote = useCallback(
    async (id: string) => {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "deleteNote", id }),
      });
      refetch();
    },
    [refetch]
  );

  const archiveNote = useCallback(
    async (id: string, archived: boolean) => {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "archiveNote", id, archived }),
      });
      refetch();
    },
    [refetch]
  );

  return { notes, loading, saveNote, deleteNote, archiveNote, refetch };
}

interface NoteEditorProps {
  note?: Note | null;
  onSave: (note: Partial<Note> & { id?: string }) => void;
  onClose: () => void;
}

function NoteEditor({ note, onSave, onClose }: NoteEditorProps) {
  const [title, setTitle] = useState(note?.title || "");
  const [content, setContent] = useState(note?.content || "");
  const [link, setLink] = useState(note?.linkContext || "");

  const handleSave = () => {
    if (!title.trim()) return;
    onSave({
      id: note?.id,
      title: title.trim(),
      content: content.trim(),
      linkContext: link.trim() || undefined,
    });
    onClose();
  };

  return (
    <div className="zeta-p-4 zeta-space-y-3">
      <div className="zeta-flex zeta-items-center zeta-justify-between">
        <h4 className="zeta-text-sm zeta-font-medium zeta-text-zeta-text">
          {note ? "메모 수정" : "새 메모"}
        </h4>
        <button
          onClick={onClose}
          className="zeta-p-1 zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text zeta-transition-colors"
        >
          <X className="zeta-w-4 zeta-h-4" />
        </button>
      </div>
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="제목"
        className="zeta-w-full zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="내용"
        rows={4}
        className="zeta-w-full zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent zeta-resize-none"
      />
      <input
        type="text"
        value={link}
        onChange={(e) => setLink(e.target.value)}
        placeholder="링크 컨텍스트 (선택)"
        className="zeta-w-full zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
      />
      <button
        onClick={handleSave}
        className="zeta-w-full zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-accent zeta-text-white zeta-rounded-lg hover:zeta-bg-zeta-accent-hover zeta-transition-colors zeta-font-medium"
      >
        저장
      </button>
    </div>
  );
}

export default function AdminNotes() {
  const { notes, saveNote, deleteNote, archiveNote } = useNotes();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  const [creating, setCreating] = useState(false);

  const popupRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef({ x: 0, y: 0, startX: 0, startY: 0, dragging: false });
  const positionRef = useRef({ x: 0, y: 0 });
  const resizeRef = useRef({ w: 380, h: 480, startX: 0, startY: 0, startW: 0, startH: 0, resizing: false });
  const sizeRef = useRef({ w: 380, h: 480 });

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (!headerRef.current?.contains(e.target as Node)) return;
    dragRef.current = {
      x: 0,
      y: 0,
      startX: e.clientX - positionRef.current.x,
      startY: e.clientY - positionRef.current.y,
      dragging: true,
    };
    e.preventDefault();
  }, []);

  const onResizeDown = useCallback((e: React.MouseEvent) => {
    resizeRef.current = {
      w: sizeRef.current.w,
      h: sizeRef.current.h,
      startX: e.clientX,
      startY: e.clientY,
      startW: sizeRef.current.w,
      startH: sizeRef.current.h,
      resizing: true,
    };
    e.preventDefault();
    e.stopPropagation();
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (dragRef.current.dragging) {
        positionRef.current = {
          x: e.clientX - dragRef.current.startX,
          y: e.clientY - dragRef.current.startY,
        };
        if (popupRef.current) {
          popupRef.current.style.right = "auto";
          popupRef.current.style.bottom = "auto";
          popupRef.current.style.left = `${positionRef.current.x}px`;
          popupRef.current.style.top = `${positionRef.current.y}px`;
        }
      }
      if (resizeRef.current.resizing) {
        sizeRef.current = {
          w: Math.max(300, resizeRef.current.startW + (e.clientX - resizeRef.current.startX)),
          h: Math.max(300, resizeRef.current.startH + (e.clientY - resizeRef.current.startY)),
        };
        if (popupRef.current) {
          popupRef.current.style.width = `${sizeRef.current.w}px`;
          popupRef.current.style.height = `${sizeRef.current.h}px`;
        }
      }
    };
    const onUp = () => {
      dragRef.current.dragging = false;
      resizeRef.current.resizing = false;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const filtered = notes.filter((n) => {
    if (!showArchived && n.archived) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q);
  });

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "zeta-fixed zeta-bottom-6 zeta-right-6 zeta-z-50 zeta-w-12 zeta-h-12 zeta-rounded-full zeta-bg-zeta-accent zeta-text-white zeta-shadow-lg hover:zeta-bg-zeta-accent-hover zeta-transition-all zeta-flex zeta-items-center zeta-justify-center",
          open && "zeta-rotate-90"
        )}
      >
        <StickyNote className="zeta-w-5 zeta-h-5" />
      </button>

      {open && (
        <div
          ref={popupRef}
          style={{ width: sizeRef.current.w, height: sizeRef.current.h }}
          className="zeta-fixed zeta-bottom-20 zeta-right-6 zeta-z-50 zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-xl zeta-shadow-2xl zeta-flex zeta-flex-col zeta-overflow-hidden"
        >
          <div
            ref={headerRef}
            onMouseDown={onMouseDown}
            className="zeta-flex zeta-items-center zeta-justify-between zeta-px-4 zeta-py-3 zeta-border-b zeta-border-zeta-border zeta-cursor-move zeta-bg-zeta-bg-secondary zeta-select-none"
          >
            <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-text-sm zeta-font-medium zeta-text-zeta-text">
              <StickyNote className="zeta-w-4 zeta-h-4" />
              메모
            </div>
            <button
              onClick={() => setOpen(false)}
              className="zeta-p-1 zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text zeta-transition-colors"
            >
              <X className="zeta-w-4 zeta-h-4" />
            </button>
          </div>

          <div className="zeta-p-3 zeta-space-y-3 zeta-flex-1 zeta-overflow-hidden zeta-flex zeta-flex-col">
            <div className="zeta-flex zeta-items-center zeta-gap-2">
              <div className="zeta-relative zeta-flex-1">
                <Search className="zeta-absolute zeta-left-2.5 zeta-top-1/2 zeta--translate-y-1/2 zeta-w-3.5 zeta-h-3.5 zeta-text-zeta-text-tertiary" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="메모 검색..."
                  className="zeta-w-full zeta-pl-8 zeta-pr-3 zeta-py-1.5 zeta-text-xs zeta-bg-zeta-bg-secondary zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
                />
              </div>
              <button
                onClick={() => setShowArchived(!showArchived)}
                className={cn(
                  "zeta-p-1.5 zeta-rounded-lg zeta-transition-colors",
                  showArchived
                    ? "zeta-bg-zeta-accent zeta-text-white"
                    : "zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text"
                )}
              >
                <Archive className="zeta-w-4 zeta-h-4" />
              </button>
              <button
                onClick={() => setCreating(true)}
                className="zeta-p-1.5 zeta-rounded-lg zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text zeta-transition-colors"
              >
                <Plus className="zeta-w-4 zeta-h-4" />
              </button>
            </div>

            {creating && (
              <NoteEditor
                note={null}
                onSave={(n) => {
                  saveNote(n);
                  setCreating(false);
                }}
                onClose={() => setCreating(false)}
              />
            )}

            {editing && (
              <NoteEditor
                note={editing}
                onSave={(n) => {
                  saveNote(n);
                  setEditing(null);
                }}
                onClose={() => setEditing(null)}
              />
            )}

            <div className="zeta-flex-1 zeta-overflow-y-auto zeta-space-y-2">
              {filtered.map((note) => (
                <div
                  key={note.id}
                  className={cn(
                    "zeta-p-3 zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-cursor-pointer hover:zeta-bg-zeta-bg-hover zeta-transition-colors",
                    note.archived && "zeta-opacity-60"
                  )}
                >
                  <div className="zeta-flex zeta-items-start zeta-justify-between zeta-gap-2">
                    <div className="zeta-flex-1 zeta-min-w-0">
                      <h4
                        className="zeta-text-sm zeta-font-medium zeta-text-zeta-text zeta-truncate"
                        onClick={() => setEditing(note)}
                      >
                        {note.title}
                      </h4>
                      <p
                        className="zeta-text-xs zeta-text-zeta-text-secondary zeta-mt-1 zeta-line-clamp-2"
                        onClick={() => setEditing(note)}
                      >
                        {note.content}
                      </p>
                      <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-mt-2">
                        <span className="zeta-text-xs zeta-text-zeta-text-tertiary">
                          {new Date(note.createdAt).toLocaleDateString("ko-KR")}
                        </span>
                        {note.linkContext && (
                          <a
                            href={note.linkContext}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="zeta-text-xs zeta-text-zeta-accent zeta-truncate"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {note.linkContext}
                          </a>
                        )}
                      </div>
                    </div>
                    <div className="zeta-flex zeta-items-center zeta-gap-1 zeta-shrink-0">
                      <button
                        onClick={() => archiveNote(note.id, !note.archived)}
                        className="zeta-p-1 zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text zeta-transition-colors"
                      >
                        <Archive className="zeta-w-3.5 zeta-h-3.5" />
                      </button>
                      <button
                        onClick={() => deleteNote(note.id)}
                        className="zeta-p-1 zeta-text-zeta-text-tertiary hover:zeta-text-red-500 zeta-transition-colors"
                      >
                        <Trash2 className="zeta-w-3.5 zeta-h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="zeta-py-8 zeta-text-center zeta-text-xs zeta-text-zeta-text-tertiary">
                  메모가 없습니다
                </div>
              )}
            </div>
          </div>

          <div
            onMouseDown={onResizeDown}
            className="zeta-absolute zeta-bottom-0 zeta-right-0 zeta-w-4 zeta-h-4 zeta-cursor-nwse-resize zeta-flex zeta-items-center zeta-justify-center zeta-text-zeta-text-tertiary"
          >
            <GripHorizontal className="zeta-w-3 zeta-h-3 zeta-rotate-45" />
          </div>
        </div>
      )}
    </>
  );
}
