"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  ClipboardCheck, Brain, AlertTriangle, MessageSquare,
  User, Eye, EyeOff, Shield, BookOpen, Pencil, Wand2,
  Plus, Edit, Trash2, Copy, ChevronUp, ChevronDown,
  Check, X, Play, Loader2,
} from "lucide-react";

interface Character { id: string; name: string; }
interface Props { characters: Character[]; selectedCharacterId: string; onNotice: (s: string) => void; onError: (s: string) => void; }
interface Example { id: string; situation: string; userInput: string; characterResponse: string; }
interface Question { id: string; text: string; result?: string; }

const TABS = [
  { id: "precheck", label: "사전 검사", icon: ClipboardCheck },
  { id: "consistency", label: "일관성 테스트", icon: Brain },
  { id: "collision", label: "충돌 검사", icon: AlertTriangle },
  { id: "examples", label: "대화 예시", icon: MessageSquare },
  { id: "speech", label: "말투 편집기", icon: Pencil },
  { id: "knowledge", label: "지식/비밀", icon: BookOpen },
];

const CHECKLIST = [
  "이미지 설정", "소개글", "성격 정의", "말투 정의", "프롬프트", "사용자 프로필", "대화 예시",
];

function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

export default function AdminCharacterTools({ selectedCharacterId, onNotice, onError }: Props) {
  const [activeTab, setActiveTab] = useState("precheck");
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  // precheck
  const [checkResults, setCheckResults] = useState<Record<number, boolean | null>>({});

  // consistency
  const [questions, setQuestions] = useState<Question[]>([]);
  const [newQuestion, setNewQuestion] = useState("");
  const [editingQId, setEditingQId] = useState<string | null>(null);
  const [editingQText, setEditingQText] = useState("");

  // collision
  const [collisions, setCollisions] = useState<{ title: string; description: string }[]>([]);

  // examples
  const [examples, setExamples] = useState<Example[]>([]);
  const [exForm, setExForm] = useState({ situation: "", userInput: "", characterResponse: "" });
  const [editingExId, setEditingExId] = useState<string | null>(null);

  // speech
  const [formality, setFormality] = useState("반말");
  const [sentenceLength, setSentenceLength] = useState(50);
  const [descriptionLevel, setDescriptionLevel] = useState(50);
  const [questionFrequency, setQuestionFrequency] = useState(50);
  const [catchphrases, setCatchphrases] = useState("");
  const [forbiddenWords, setForbiddenWords] = useState("");

  // knowledge
  const [known, setKnown] = useState("");
  const [unknown, setUnknown] = useState("");
  const [secrets, setSecrets] = useState("");
  const [learnable, setLearnable] = useState("");

  const setL = (key: string, v: boolean) => setLoading((p) => ({ ...p, [key]: v }));

  // ─── precheck ───
  const runPrecheck = async () => {
    setL("precheck", true);
    try {
      const res = await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "precheckCharacter", characterId: selectedCharacterId }),
      });
      const data = await res.json();
      if (data.results) setCheckResults(data.results);
      onNotice("사전 검사 완료");
    } catch { onError("사전 검사 실패"); }
    finally { setL("precheck", false); }
  };

  // ─── consistency ───
  const addQuestion = () => { if (!newQuestion.trim()) return; setQuestions((p) => [...p, { id: genId(), text: newQuestion.trim() }]); setNewQuestion(""); };
  const removeQuestion = (id: string) => { setQuestions((p) => p.filter((q) => q.id !== id)); if (editingQId === id) { setEditingQId(null); setEditingQText(""); } };
  const saveEditQuestion = () => { if (!editingQId || !editingQText.trim()) return; setQuestions((p) => p.map((q) => (q.id === editingQId ? { ...q, text: editingQText.trim() } : q))); setEditingQId(null); setEditingQText(""); };
  const runQuestionTest = async (q: Question) => {
    setL(`q-${q.id}`, true);
    try {
      const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: q.text, characterId: selectedCharacterId, mode: "consistency" }) });
      const data = await res.json();
      setQuestions((p) => p.map((x) => (x.id === q.id ? { ...x, result: data.passed ? "pass" : "fail" } : x)));
    } catch { onError("테스트 실행 실패"); }
    finally { setL(`q-${q.id}`, false); }
  };

  // ─── collision ───
  const checkCollisions = async () => {
    setL("collision", true);
    try {
      const res = await fetch("/api/admin/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "checkCollisions", characterId: selectedCharacterId }) });
      const data = await res.json();
      setCollisions(data.collisions || []);
      onNotice("충돌 검사 완료");
    } catch { onError("충돌 검사 실패"); }
    finally { setL("collision", false); }
  };

  // ─── examples ───
  const resetExForm = () => { setExForm({ situation: "", userInput: "", characterResponse: "" }); setEditingExId(null); };
  const addExample = () => { if (!exForm.situation.trim() || !exForm.userInput.trim() || !exForm.characterResponse.trim()) return; setExamples((p) => [...p, { id: genId(), ...exForm }]); resetExForm(); };
  const startEditExample = (ex: Example) => { setEditingExId(ex.id); setExForm({ situation: ex.situation, userInput: ex.userInput, characterResponse: ex.characterResponse }); };
  const saveEditExample = () => { if (!editingExId) return; setExamples((p) => p.map((ex) => (ex.id === editingExId ? { ...ex, ...exForm } : ex))); resetExForm(); };
  const cloneExample = (ex: Example) => setExamples((p) => [...p, { ...ex, id: genId() }]);
  const deleteExample = (id: string) => { setExamples((p) => p.filter((ex) => ex.id !== id)); if (editingExId === id) resetExForm(); };
  const moveExample = (i: number, d: -1 | 1) => setExamples((p) => { const a = [...p]; const t = i + d; if (t < 0 || t >= a.length) return a; [a[i], a[t]] = [a[t], a[i]]; return a; });

  // ─── speech ───
  const saveSpeech = async () => {
    setL("speech", true);
    try {
      await fetch("/api/admin/content", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "saveCharacterSpeech", characterId: selectedCharacterId, formality, sentenceLength, descriptionLevel, questionFrequency, catchphrases, forbiddenWords }) });
      onNotice("말투 설정 저장됨");
    } catch { onError("말투 저장 실패"); }
    finally { setL("speech", false); }
  };
  const testSpeech = async () => {
    setL("speechTest", true);
    try {
      const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: "안녕! 자기소개 해줄래?", characterId: selectedCharacterId, mode: "speech-test", settings: { formality, sentenceLength, descriptionLevel, questionFrequency, catchphrases, forbiddenWords } }) });
      const data = await res.json();
      onNotice(`말투 테스트 응답: ${data.response?.slice(0, 100)}...`);
    } catch { onError("말투 테스트 실패"); }
    finally { setL("speechTest", false); }
  };

  // ─── knowledge ───
  const saveKnowledge = async () => {
    setL("knowledge", true);
    try {
      await fetch("/api/admin/content", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "saveCharacterExtended", characterId: selectedCharacterId, known, unknown, secrets, learnable }) });
      onNotice("지식/비밀 저장됨");
    } catch { onError("지식/비밀 저장 실패"); }
    finally { setL("knowledge", false); }
  };

  const rangeSlider = (label: string, v: number, onChange: (v: number) => void) => (
    <div>
      <div className="flex justify-between text-xs mb-0.5"><span>{label}</span><span className="zeta-text-muted">{v}%</span></div>
      <input type="range" min={0} max={100} value={v} onChange={(e) => onChange(+e.target.value)} className="w-full" />
    </div>
  );

  const textarea = (label: string, value: string, onChange: (v: string) => void, rows = 3, placeholder = "") => (
    <div>
      <label className="text-xs font-medium block mb-0.5">{label}</label>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} placeholder={placeholder} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y" />
    </div>
  );

  const inputField = (label: string, value: string, onChange: (v: string) => void, placeholder = "") => (
    <div>
      <label className="text-xs font-medium block mb-0.5">{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm" />
    </div>
  );

  return (
    <div className="zeta-card border zeta-border rounded-lg">
      <div className="zeta-tabs flex border-b zeta-border overflow-x-auto">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn("zeta-tab flex items-center gap-1.5 px-3 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors",
              activeTab === tab.id ? "zeta-tab-active border-zeta-accent text-zeta-accent" : "border-transparent zeta-text-muted hover:text-zeta-text")}>
            <tab.icon className="w-4 h-4" />{tab.label}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-3">
        {/* ══════ 사전 검사 ══════ */}
        {activeTab === "precheck" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><ClipboardCheck className="w-5 h-5" />사전 검사</h3>
            <div className="border zeta-border rounded-lg divide-y zeta-border">
              {CHECKLIST.map((label, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {checkResults[i] === true ? <Check className="w-4 h-4 text-green-500" /> : checkResults[i] === false ? <AlertTriangle className="w-4 h-4 text-yellow-500" /> : <div className="w-4 h-4 rounded-full border zeta-border" />}
                    <span className="text-sm">{label}</span>
                  </div>
                  {checkResults[i] !== undefined && <span className={cn("text-xs px-1.5 py-0.5 rounded", checkResults[i] ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700")}>{checkResults[i] ? "완료" : "미흡"}</span>}
                </div>
              ))}
            </div>
            <button onClick={runPrecheck} disabled={loading.precheck} className="zeta-btn zeta-btn-primary inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
              {loading.precheck ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}테스트 실행
            </button>
          </div>
        )}

        {/* ══════ 일관성 테스트 ══════ */}
        {activeTab === "consistency" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><Brain className="w-5 h-5" />일관성 테스트</h3>
            <div className="flex gap-2">
              <input value={newQuestion} onChange={(e) => setNewQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addQuestion()} placeholder="테스트 질문 입력..." className="zeta-input flex-1 px-3 py-1.5 border zeta-border rounded-lg text-sm" />
              <button onClick={addQuestion} className="zeta-btn zeta-btn-primary inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm"><Plus className="w-4 h-4" />추가</button>
            </div>
            {questions.length === 0 ? <p className="text-sm zeta-text-muted text-center py-4">테스트 질문을 추가해주세요</p> : questions.map((q) => (
              <div key={q.id} className="border zeta-border rounded-lg p-3">
                {editingQId === q.id ? (
                  <div className="flex gap-2">
                    <input value={editingQText} onChange={(e) => setEditingQText(e.target.value)} className="zeta-input flex-1 px-2 py-1 border zeta-border rounded text-sm" />
                    <button onClick={saveEditQuestion} className="p-1 text-green-600"><Check className="w-4 h-4" /></button>
                    <button onClick={() => { setEditingQId(null); setEditingQText(""); }} className="p-1 zeta-text-muted"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{q.text}</span>
                    <div className="flex items-center gap-1">
                      {q.result && <span className={cn("text-xs px-1.5 py-0.5 rounded", q.result === "pass" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700")}>{q.result === "pass" ? "통과" : "실패"}</span>}
                      <button onClick={() => runQuestionTest(q)} disabled={loading[`q-${q.id}`]} className="p-1 zeta-text-muted hover:text-zeta-accent disabled:opacity-50">{loading[`q-${q.id}`] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}</button>
                      <button onClick={() => { setEditingQId(q.id); setEditingQText(q.text); }} className="p-1 zeta-text-muted hover:text-zeta-text"><Edit className="w-3.5 h-3.5" /></button>
                      <button onClick={() => removeQuestion(q.id)} className="p-1 zeta-text-muted hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ══════ 충돌 검사 ══════ */}
        {activeTab === "collision" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><AlertTriangle className="w-5 h-5" />충돌 검사</h3>
            <button onClick={checkCollisions} disabled={loading.collision} className="zeta-btn zeta-btn-primary inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
              {loading.collision ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}설정 충돌 검사
            </button>
            {collisions.length > 0 && (
              <div className="border zeta-border rounded-lg divide-y zeta-border">
                {collisions.map((c, i) => (
                  <div key={i} className="px-4 py-3 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 shrink-0" />
                    <div><p className="text-sm font-medium">{c.title}</p><p className="text-xs zeta-text-muted">{c.description}</p></div>
                  </div>
                ))}
              </div>
            )}
            {collisions.length === 0 && !loading.collision && <p className="text-sm zeta-text-muted">충돌 검사를 실행해주세요</p>}
          </div>
        )}

        {/* ══════ 대화 예시 ══════ */}
        {activeTab === "examples" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><MessageSquare className="w-5 h-5" />대화 예시</h3>
            <div className="border zeta-border rounded-lg p-3 space-y-2">
              {inputField("상황", exForm.situation, (v) => setExForm((p) => ({ ...p, situation: v })), "예: 첫 만남")}
              {inputField("사용자 입력", exForm.userInput, (v) => setExForm((p) => ({ ...p, userInput: v })))}
              {textarea("캐릭터 응답", exForm.characterResponse, (v) => setExForm((p) => ({ ...p, characterResponse: v })), 2)}
              <div className="flex gap-2">
                {editingExId ? (
                  <><button onClick={saveEditExample} className="zeta-btn zeta-btn-primary px-3 py-1.5 rounded-lg text-sm">저장</button>
                    <button onClick={resetExForm} className="zeta-btn px-3 py-1.5 rounded-lg text-sm border zeta-border">취소</button></>
                ) : (
                  <button onClick={addExample} className="zeta-btn zeta-btn-primary px-3 py-1.5 rounded-lg text-sm inline-flex items-center gap-1"><Plus className="w-4 h-4" />추가</button>
                )}
              </div>
            </div>
            {examples.length === 0 ? <p className="text-sm zeta-text-muted text-center py-4">대화 예시를 추가해주세요</p> : examples.map((ex, i) => (
              <div key={ex.id} className="border zeta-border rounded-lg p-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1 min-w-0 flex-1">
                    <span className="text-xs font-medium text-zeta-accent bg-zeta-accent/10 px-1.5 py-0.5 rounded">{ex.situation}</span>
                    <p className="text-sm zeta-text-muted"><User className="w-3 h-3 inline mr-1" />{ex.userInput}</p>
                    <p className="text-sm">{ex.characterResponse}</p>
                  </div>
                  <div className="flex items-center gap-0.5 ml-2 shrink-0">
                    <button onClick={() => moveExample(i, -1)} disabled={i === 0} className="p-1 zeta-text-muted hover:text-zeta-text disabled:opacity-30"><ChevronUp className="w-3.5 h-3.5" /></button>
                    <button onClick={() => moveExample(i, 1)} disabled={i === examples.length - 1} className="p-1 zeta-text-muted hover:text-zeta-text disabled:opacity-30"><ChevronDown className="w-3.5 h-3.5" /></button>
                    <button onClick={() => startEditExample(ex)} className="p-1 zeta-text-muted hover:text-zeta-text"><Edit className="w-3.5 h-3.5" /></button>
                    <button onClick={() => cloneExample(ex)} className="p-1 zeta-text-muted hover:text-zeta-text"><Copy className="w-3.5 h-3.5" /></button>
                    <button onClick={() => deleteExample(ex.id)} className="p-1 zeta-text-muted hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ══════ 말투 편집기 ══════ */}
        {activeTab === "speech" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><Pencil className="w-5 h-5" />말투 편집기</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium block mb-1">존댓말/반말</label>
                <div className="flex gap-2">
                  {["반말", "존댓말", "혼용"].map((opt) => (
                    <button key={opt} onClick={() => setFormality(opt)} className={cn("px-3 py-1.5 rounded-lg text-sm border transition-colors", formality === opt ? "zeta-btn-primary border-zeta-accent bg-zeta-accent text-white" : "zeta-btn border-zeta-border hover:border-zeta-accent")}>{opt}</button>
                  ))}
                </div>
              </div>
              {rangeSlider("문장 길이", sentenceLength, setSentenceLength)}
              {rangeSlider("묘사 수준", descriptionLevel, setDescriptionLevel)}
              {rangeSlider("질문 빈도", questionFrequency, setQuestionFrequency)}
              {textarea("입버릇/캐치프레이즈", catchphrases, setCatchphrases, 2, "줄바꿈으로 구분...")}
              {textarea("금지 표현", forbiddenWords, setForbiddenWords, 2, "줄바꿈으로 구분...")}
              <div className="flex gap-2">
                <button onClick={saveSpeech} disabled={loading.speech} className="zeta-btn zeta-btn-primary px-4 py-1.5 rounded-lg text-sm inline-flex items-center gap-1.5 disabled:opacity-50">{loading.speech ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}저장</button>
                <button onClick={testSpeech} disabled={loading.speechTest} className="zeta-btn px-4 py-1.5 rounded-lg text-sm border zeta-border inline-flex items-center gap-1.5 disabled:opacity-50">{loading.speechTest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}말투 테스트</button>
              </div>
            </div>
          </div>
        )}

        {/* ══════ 지식/비밀 ══════ */}
        {activeTab === "knowledge" && (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2"><BookOpen className="w-5 h-5" />지식/비밀</h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium flex items-center gap-1.5 mb-0.5"><Eye className="w-3.5 h-3.5" />알고 있는 것</label>
                <textarea value={known} onChange={(e) => setKnown(e.target.value)} rows={3} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y" />
              </div>
              <div>
                <label className="text-xs font-medium flex items-center gap-1.5 mb-0.5"><EyeOff className="w-3.5 h-3.5" />모르는 것</label>
                <textarea value={unknown} onChange={(e) => setUnknown(e.target.value)} rows={3} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y" />
              </div>
              <div>
                <label className="text-xs font-medium flex items-center gap-1.5 mb-0.5"><Shield className="w-3.5 h-3.5" />비밀</label>
                <textarea value={secrets} onChange={(e) => setSecrets(e.target.value)} rows={3} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y" />
              </div>
              <div>
                <label className="text-xs font-medium flex items-center gap-1.5 mb-0.5"><BookOpen className="w-3.5 h-3.5" />배울 수 있는 것</label>
                <textarea value={learnable} onChange={(e) => setLearnable(e.target.value)} rows={3} className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y" />
              </div>
              <button onClick={saveKnowledge} disabled={loading.knowledge} className="zeta-btn zeta-btn-primary px-4 py-2 rounded-lg text-sm inline-flex items-center gap-1.5 disabled:opacity-50">{loading.knowledge ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}저장</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
