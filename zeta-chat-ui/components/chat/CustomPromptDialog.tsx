import { ChevronDown, Save, X } from "lucide-react";

type CustomPromptDialogProps = {
  appendDraft: string;
  savedDraft: string;
  onAppendChange: (value: string) => void;
  onAppendSave: () => void;
  onCancel: () => void;
  onClearAppend: () => void;
};

export function CustomPromptDialog({
  appendDraft,
  savedDraft,
  onAppendChange,
  onAppendSave,
  onCancel,
  onClearAppend,
}: CustomPromptDialogProps) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 px-4">
      <section className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel shadow-zeta">
        <div className="flex items-center justify-between gap-3 border-b border-zeta-line px-4 py-3">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-zeta-text">
              캐릭터 설정
            </h2>
            <p className="mt-1 text-xs text-zeta-muted">
              이 설정은 현재 대화방에만 적용됩니다.
            </p>
          </div>
          <button
            aria-label="닫기"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-zeta-line text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onCancel}
            type="button"
          >
            <X size={20} />
          </button>
        </div>

        <div className="max-h-[calc(90vh-4rem)] space-y-3 overflow-y-auto p-4">
          <details
            className="group rounded-lg border border-zeta-line bg-zeta-panel2"
            open
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-zeta-text marker:hidden">
              이번 대화에 추가할 내용
              <ChevronDown
                aria-hidden="true"
                className="shrink-0 text-zeta-muted transition group-open:rotate-180"
                size={18}
              />
            </summary>
            <div className="space-y-2 border-t border-zeta-line p-4">
              <textarea
                className="textarea min-h-32"
                id="custom-prompt-append"
                onChange={(event) => onAppendChange(event.target.value)}
                placeholder="예: 이 대화에서는 더 장난스럽게 말해줘. 장면 묘사는 짧게 유지해줘."
                value={appendDraft}
              />
              <div className="flex flex-wrap justify-end gap-2">
                <button
                  className="h-10 rounded-lg border border-zeta-line px-4 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel hover:text-zeta-text"
                  onClick={onClearAppend}
                  type="button"
                >
                  비우기
                </button>
                <button
                  className="inline-flex h-10 items-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!appendDraft.trim()}
                  onClick={onAppendSave}
                  type="button"
                >
                  <Save size={16} />
                  저장
                </button>
              </div>
            </div>
          </details>

          <details
            className="group rounded-lg border border-zeta-line bg-zeta-panel2"
            open
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-zeta-text marker:hidden">
              저장된 대화 설정
              <ChevronDown
                aria-hidden="true"
                className="shrink-0 text-zeta-muted transition group-open:rotate-180"
                size={18}
              />
            </summary>
            <div className="border-t border-zeta-line p-4">
              <textarea
                aria-label="저장된 대화 설정"
                className="textarea min-h-48 cursor-default bg-zeta-panel text-zeta-muted"
                id="custom-prompt-saved"
                placeholder="아직 이 대화에만 적용되는 설정이 없습니다."
                readOnly
                value={savedDraft}
              />
            </div>
          </details>

          <div className="flex justify-end">
            <button
              className="h-10 rounded-lg border border-zeta-line px-4 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
              onClick={onCancel}
              type="button"
            >
              닫기
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
