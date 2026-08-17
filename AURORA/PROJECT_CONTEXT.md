# PROJECT CONTEXT — AURORA (zeta-chat-ui)

> 이 문서를 먼저 읽으면 프로젝트 구조와 규칙을 빠르게 이해할 수 있습니다.
> 추정/미확인 항목에는 `[확인 필요]` 표시. 이외는 모두 실제 코드에서 확인된 사실.

---

## 1. 프로젝트 목적과 기술 스택

- **목적**: Zeta 스타일 AI 캐릭터 챗봇 UI. 사용자가 여러 캐릭터(챗봇)와 한국어로 대화.
- **배포 주소**: `https://zeta.dcout.site` (Next.js 서버 + Caddy 리버스 프록시)
- **로컬 개발**: `npm run dev` → `http://127.0.0.1:3000`

### 기술 스택

| 계층 | 기술 | 버전 | 확인 근거 |
|------|------|------|-----------|
| 프레임워크 | Next.js (App Router) | 15.1.12 | `package.json` |
| UI 라이브러리 | React | 19.0.0 | `package.json` |
| 언어 | TypeScript | 5.8.2 | `package.json` |
| CSS | Tailwind CSS | 3.4.17 | `package.json`, `tailwind.config.ts` |
| 아이콘 | Lucide React | 0.468.0 | `package.json` |
| 유틸리티 | clsx, tailwind-merge | - | `lib/utils.ts` |
| 테스트 | Playwright | 1.61.1 (devDeps, 미사용) | `package.json`, 테스트 파일 없음 |
| DB | 없음 (파일 기반 JSON/JSONL) | - | `lib/server-files.ts`, `data/` |
| ORM | 없음 | - | 의존성 없음, 코드 확인 |

---

## 2. 전체 폴더 구조

```
AURORA/
├── app/                         # Next.js App Router (프런트엔드 페이지 + API 라우트)
│   ├── layout.tsx               # 루트 레이아웃, PWA 메타데이터, 테마 초기화 스크립트
│   ├── page.tsx                 # 루트 페이지 (ChatLayout 렌더링)
│   ├── globals.css              # CSS 커스텀 프로퍼티, Tailwind 지시어, 모바일 오버라이드
│   ├── admin/page.tsx           # /admin 관리자 페이지 (클라이언트 컴포넌트)
│   ├── pwa/page.tsx             # /pwa PWA 설치 가이드 페이지
│   └── api/                     # 13개 API 엔드포인트 (자세한 목록은 §4 참조)
│       ├── chat/route.ts        # 메인 채팅 API (POST, SSE 스트리밍 포함)
│       ├── chatbots/route.ts    # 챗봇 목록 + 응답 옵션 제공 (GET)
│       ├── models/route.ts      # AI 제공자 모델 검색 (GET)
│       ├── auth/                # 인증 (login, logout, register, session)
│       ├── account/             # 계정 관리 (profile, response, rooms)
│       └── admin/               # 관리자 API (chatbots, chats, prompts)
├── components/                  # 15개 React 컴포넌트
│   ├── chat/                    # 13개 채팅 UI 컴포넌트
│   │   ├── ChatLayout.tsx       # 메인 상태 관리자 (1065줄, 가장 큰 컴포넌트)
│   │   ├── ChatSidebar.tsx      # 채팅방 목록, 새 채팅 생성
│   │   ├── ChatHeader.tsx       # 응답 스타일, 캐릭터 설정, 관리자 링크
│   │   ├── ChatInput.tsx        # 메시지 입력, 전송, 턴 건너뛰기
│   │   ├── MessageList.tsx      # 메시지 리스트 렌더링
│   │   ├── MessageBubble.tsx    # 개별 메시지 버블
│   │   ├── HomeDiscover.tsx     # 챗봇 선택 화면
│   │   ├── AuthPanel.tsx        # 로그인/회원가입 패널
│   │   ├── AccountSettingsDialog.tsx  # 계정 설정 모달
│   │   ├── CustomPromptDialog.tsx     # 커스텀 캐릭터 프롬프트 모달
│   │   ├── ThemeSelector.tsx    # 테마 선택기
│   │   ├── BotAvatar.tsx        # 챗봇 아바타
│   │   └── MobileNav.tsx        # 모바일 하단 네비게이션
│   ├── admin/
│   │   └── AdminWidgets.tsx     # 관리자 페이지 공통 위젯 (페이징, 타임라인 등)
│   └── pwa/
│       └── PwaInstallPanel.tsx  # PWA 설치 안내 패널
├── lib/                         # 24개 비즈니스 로직 파일
│   ├── chat-memory.ts           # 메모리 저장소, RAG 컨텍스트, 관계 추적 (1567줄)
│   ├── chat-provider.ts         # AI 제공자 라우팅, API 호출, SSE/Ollama 스트림 파싱
│   ├── chat-prompts.ts          # 시스템 프롬프트 조립, 모델 컨텍스트 윈도우 관리
│   ├── chat-request.ts          # 채팅 요청 파싱/검증
│   ├── chat-response.ts         # 응답 길이 제한, 스트림 클램핑, 토큰 예산
│   ├── chat-api.ts              # 브라우저용 SSE 스트림 파서 (클라이언트 사이드)
│   ├── chat-logs.ts             # JSONL 기반 대화 로그 저장/조회
│   ├── chat-persistence.ts      # 성공적 턴 저장 (채팅방, 메모리, 로그)
│   ├── chat-memory-extraction.ts # LLM 기반 메모리 업데이트 프롬프트/파서
│   ├── chat-memory-ranking.ts   # BM25 기반 메모리 문서 랭킹 (한글 토크나이저)
│   ├── auth.ts                  # 파일 기반 인증 (scrypt 해시, 세션 쿠키)
│   ├── admin-auth.ts            # 관리자 Bearer 토큰 인증
│   ├── account-data.ts          # 사용자별 채팅방, 메모리, 응답 스타일 저장
│   ├── bot-config.ts            # 챗봇 설정 정규화/저장 (chatbots.json)
│   ├── prompt-store.ts          # 프롬프트 섹션/카테고리 관리 (response-prompts.txt)
│   ├── provider-settings.ts     # 제공자 설정 (DeepSeek API 키 등)
│   ├── runtime-models.ts        # LM Studio/Ollama 모델 검색, URL 해석
│   ├── response-formats.ts      # 응답 스타일 옵션 (flavor × length)
│   ├── response-prompt-builder.ts # 응답 스타일별 프롬프트 조립
│   ├── server-files.ts          # 파일 I/O 유틸 (원자적 쓰기, 잠금, JSON 파싱)
│   ├── rate-limit.ts            # in-memory IP 기반 API 속도 제한
│   ├── themes.ts                # 7개 UI 테마 정의
│   ├── mock-data.ts             # 기본 챗봇/캐릭터 데이터 (실제로는 기본 설정값)
│   └── utils.ts                 # cn() = clsx + tailwind-merge
├── types/
│   └── chat.ts                  # 모든 TypeScript 타입 정의 (207줄)
├── data/                        # 런타임 데이터 (gitignore 대상)
│   ├── chatbots.json            # 챗봇/캐릭터 설정
│   ├── chat-logs.jsonl          # 전체 대화 로그
│   ├── auth-users.json          # 사용자 계정 (비밀번호 해시 포함)
│   ├── auth-sessions.json       # 활성 세션
│   ├── provider-settings.json   # 제공자 설정
│   ├── prompt-categories.json   # 프롬프트 카테고리
│   ├── response-prompts.txt     # 프롬프트 섹션 텍스트
│   ├── accounts/{userId}/       # 사용자별 데이터
│   │   ├── rooms.json           # 채팅방 목록
│   │   ├── memories.jsonl       # 메모리 아이템
│   │   └── response-style.json  # 응답 스타일
│   └── memory/chats/{chatId}/   # 채팅별 장기 메모리
│       ├── state.json           # 메모리 상태 (요약, 프로필, 이벤트, 그래프)
│       ├── relationship.json    # 관계 상태
│       ├── turns.jsonl          # 전체 대화 턴
│       └── documents.jsonl      # RAG 검색용 문서
├── public/                      # 정적 파일
│   ├── manifest.webmanifest     # PWA 매니페스트
│   ├── sw.js                    # Service Worker
│   └── icons/                   # 앱 아이콘 (SVG, 192px, 512px)
├── scripts/                     # 운영/배포 스크립트
│   ├── next-build.mjs           # 빌드 안정성 래퍼 (BUILD_ID 보정)
│   ├── deploy-zeta-root.sh      # 프로덕션 배포 (systemd + Caddy)
│   ├── backup-zeta-data.sh      # 데이터 디렉토리 백업
│   ├── ollama-reverse-tunnel.ps1     # Windows→Pi Ollama SSH 터널
│   ├── lmstudio-reverse-tunnel.ps1   # Windows→Pi LM Studio SSH 터널
│   ├── lmstudio-logging-proxy.cjs    # LM Studio 로깅 프록시
│   └── install-lmstudio-tunnel-task.ps1  # 터널 Windows 예약 작업
├── docs/
│   ├── file-map.md              # 파일별 역할 가이드
│   ├── current-state.md         # 현재 상태 문서
│   └── operations.md            # 운영 절차 (데이터 이전, 백업, 터널)
├── pages/                       # 비어 있음 (Pages Router 미사용)
├── tmp/                         # 임시 파일 (gitignore)
├── .next/                       # 빌드 출력 (gitignore)
├── node_modules/                # 의존성 (gitignore)
├── node_modules_bak_20260630072725/  # 오래된 node_modules 백업
├── .codex-backups/              # Codex 에이전트 백업
├── .deploy-backups/             # 배포 백업 아카이브
├── .codex-remote-attachments/   # Codex 첨부 파일
├── .env.example                 # 환경 변수 템플릿 (참고용, 실제 .env는 gitignore)
├── .eslintrc.json               # ESLint 설정 (next/core-web-vitals + typescript)
├── .gitignore
├── next.config.mjs              # Next.js 설정 (outputFileTracingRoot)
├── tsconfig.json                # TypeScript 설정 (경로 별칭 @/*)
├── tailwind.config.ts           # Tailwind 설정 (zeta 색상/그림자)
├── postcss.config.mjs           # PostCSS 설정
├── package.json                 # 의존성 및 스크립트
├── package-lock.json
├── AGENTS.md                    # 프로젝트별 Codex 지침
└── README.md                    # 프로젝트 개요
```

---

## 3. 주요 페이지와 라우팅 (프런트엔드)

| 경로 | 파일 | 컴포넌트 | 접근 제한 |
|------|------|----------|-----------|
| `/` | `app/page.tsx` | `ChatLayout` | 없음 (선택적 인증) |
| `/admin` | `app/admin/page.tsx` | AdminPage (CSR) | `ADMIN_TOKEN` Bearer 인증 |

- `pages/` 디렉토리는 완전히 비어 있음 → Pages Router 미사용
- `ChatLayout`이 실질적 메인 앱: 채팅 상태, 스트리밍, 인증, 채팅방 관리 모두 포함

---

## 4. API 엔드포인트

### 공개 엔드포인트 (인증 불필요)

| 메서드 | 경로 | 역할 | 속도 제한 |
|--------|------|------|-----------|
| POST | `/api/chat` | 채팅 응답 생성 (SSE 스트리밍) | 30 req/min |
| GET | `/api/chatbots` | 챗봇 목록 + 응답 옵션 | - |
| GET | `/api/models` | AI 모델 검색 (LM Studio/Ollama/OpenAI/DeepSeek) | 60 req/min |
| POST | `/api/auth/login` | 로그인 → 세션 쿠키 | 8 req/5min |
| POST | `/api/auth/register` | 회원가입 → 세션 쿠키 | 5 req/10min |
| POST | `/api/auth/logout` | 로그아웃 | - |
| GET | `/api/auth/session` | 현재 세션 확인 | - |

### 사용자 인증 필요 (세션 쿠키)

| 메서드 | 경로 | 역할 | 속도 제한 |
|--------|------|------|-----------|
| PATCH | `/api/account/profile` | 사용자 이름 변경 | - |
| GET | `/api/account/response` | 응답 스타일 조회 | - |
| POST | `/api/account/response` | 응답 스타일 저장 | 120 req/min |
| POST | `/api/account/rooms` | 채팅방 저장 | 120 req/min |
| DELETE | `/api/account/rooms?roomId=` | 채팅방 삭제 | 120 req/min |

### 관리자 인증 필요 (Authorization: Bearer {ADMIN_TOKEN})

| 메서드 | 경로 | 역할 | 속도 제한 |
|--------|------|------|-----------|
| GET | `/api/admin/chatbots` | 챗봇 설정 조회 | 60 req/min |
| POST | `/api/admin/chatbots` | 챗봇 설정 저장 (캐릭터, 모델, DeepSeek 키) | 60 req/min |
| GET | `/api/admin/chats?limit=` | 대화 로그 조회 | 60 req/min |
| GET | `/api/admin/prompts` | 프롬프트 섹션 조회 | 60 req/min |
| POST | `/api/admin/prompts` | 프롬프트 섹션/카테고리 저장 | 60 req/min |

---

## 5. 핵심 lib 파일과 역할

### 채팅 파이프라인 (사용자 메시지 → AI 응답)

```
chat-request.ts → 요청 파싱/검증
  ↓
chat-prompts.ts → 시스템 프롬프트 + 사용자 메시지 + 메모리 컨텍스트 조립
  ↓
chat-provider.ts → AI 제공자 라우팅 (getProviderRuntime) → API 호출 → 스트림 파싱
  ↓
chat-response.ts → 응답 길이 제한 (단문/중문/장문), 토큰 버짓, SSE 클램핑
  ↓
chat-persistence.ts → 채팅방 저장, 메모리 아이템 생성, 로그 엔트리
  ↓
chat-memory.ts → 비동기 메모리 업데이트 (턴 기록, 상태 갱신, 문서 압축)
```

### 데이터 저장 계층

```
server-files.ts → readJsonFile, writeJsonFile, writeTextFile, withFileLock
  ├── auth.ts              (auth-users.json, auth-sessions.json)
  ├── bot-config.ts         (chatbots.json)
  ├── account-data.ts       (accounts/{userId}/rooms.json, memories.jsonl)
  ├── chat-logs.ts          (chat-logs.jsonl)
  ├── prompt-store.ts       (response-prompts.txt, prompt-categories.json)
  ├── provider-settings.ts  (provider-settings.json)
  └── chat-memory.ts        (memory/chats/{chatId}/*.json, *.jsonl)
```

### 제공자/모델 계층

```
runtime-models.ts → LM Studio/Ollama 모델 패치, 캐싱, URL 해석
provider-settings.ts → DeepSeek API 키 저장
bot-config.ts → 챗봇별 모델 매핑 저장
chat-provider.ts → 제공자 라우팅 (AI_PROVIDER 기준), API 호출
```

---

## 6. 채팅 생성 및 SSE 스트리밍 흐름

```
1. 클라이언트 POST /api/chat (JSON 바디에 messages, character, responseStyle 등)
2. rate-limit 검사 (IP 기반)
3. chat-request.ts: parseChatRequest() → ParsedChatRequest
4. chat-provider.ts: getProviderRuntime(character.modelId, modelSelection)
   → AI_PROVIDER 환경 변수 기반 제공자 선택
   → LM Studio/Ollama: 로컬 API URL + 모델 이름
   → OpenAI/DeepSeek: 원격 API URL + API 키
5. chat-memory.ts: buildMemoryContext() → RAG 메모리 검색 결과
6. chat-prompts.ts: buildLmStudioMessages() → 시스템 프롬프트 조립
   → 페르소나 + 응답 스타일 + 길이 계약 + 메모리 컨텍스트 + 최근 메시지
7-a. stream=true → createStreamingChatResponse()
   → SSE ReadableStream 생성
   → "event: token\ndata: {"content":"글자"}\n\n" 형식
   → Intl.Segmenter로 한글 grapheme 단위 분할
   → STREAM_TOKEN_DELAY_MS 지연 적용
   → createResponseStreamLimiter()로 길이 제한 중도 끊기
7-b. stream=false → createChatCompletion() → JSON 응답
8. 폴백: 모델 실패 시 fallbackModel로 자동 재시도 (chat-provider.ts)
9. 완료 후:
   → chat-persistence.ts: 채팅방 저장, 메모리 아이템 생성
   → chat-logs.ts: JSONL 로그 append
   → chat-memory.ts: 비동기 메모리 업데이트 큐잉
```

---

## 7. 데이터 저장 구조 (JSON/JSONL)

### 파일 기반, 관계형 DB 없음

- **모든 데이터는 `CHAT_LOG_DIR` (기본값: `./data/`) 아래에 저장**
- `server-files.ts`가 원자적 쓰기(`withFileLock` → temp 파일 → rename), JSON/JSONL 읽기 제공
- 프로덕션: `CHAT_LOG_DIR=/var/lib/zeta-next-ui/data`

### 주요 데이터 파일

| 파일 | 형식 | 내용 |
|------|------|------|
| `chatbots.json` | JSON | 챗봇 모델, 캐릭터, 기본 캐릭터 ID |
| `chat-logs.jsonl` | JSONL | 모든 대화 턴 로그 (관리자 페이지용) |
| `auth-users.json` | JSON 배열 | 사용자 ID, 이름, scrypt 해시된 비밀번호 |
| `auth-sessions.json` | JSON 배열 | 세션 토큰 SHA-256 해시, 만료일 |
| `provider-settings.json` | JSON | DeepSeek API 키 |
| `prompt-categories.json` | JSON | 응답 카테고리, 할당 |
| `response-prompts.txt` | 텍스트 | `{section.key}\n내용` 형식 |
| `accounts/{userId}/rooms.json` | JSON 배열 | 사용자별 채팅방 |
| `accounts/{userId}/memories.jsonl` | JSONL | 메모리 아이템 |
| `accounts/{userId}/response-style.json` | JSON | 사용자 응답 스타일 |
| `memory/chats/{chatId}/state.json` | JSON | 메모리 상태 (전체) |
| `memory/chats/{chatId}/relationship.json` | JSON | 관계 상태 |
| `memory/chats/{chatId}/turns.jsonl` | JSONL | 대화 턴 전체 |
| `memory/chats/{chatId}/documents.jsonl` | JSONL | RAG 검색용 문서 |

---

## 8. 기억 시스템 (Memory)과 RAG

### 저장소 구조
```
memory/chats/{chatId}/
  state.json       → ChatMemoryState (요약, 프로필, 선호도, 이벤트, 그래프 엣지, 청크)
  relationship.json → MemoryRelationship (친밀도 0~1, 신뢰도 0~1, 분위기, 동적, 열린 루프, 경계)
  turns.jsonl       → [{ id, createdAt, userContent, assistantContent, messages }]
  documents.jsonl   → [{ id, kind, text, importance 0~1, createdAt }]
```

### 작동 흐름
```
1. 매 턴: appendMemoryTurn() → turns.jsonl + documents.jsonl에 turn 기록
2. 큐잉: enqueueMemoryStateUpdate() → 5분 idle 후 flush
3-a. MEMORY_LLM_ENABLED=1: LLM이 상태 업데이트 (chat-memory-extraction.ts)
     → 현재 상태 + 최근 메시지를 프롬프트로 → LLM 응답 → parseMemoryUpdate()
3-b. MEMORY_LLM_ENABLED=0 (기본값): 규칙 기반 추출만
     → 정규식으로 이름, 취향, 장치 등 간단 프로필 추출
4. 검색: buildMemoryContext() → 사용자 질의 분석
   → 선택적 검색 트리거: 한국어 키워드, 최소 길이 24자
   → BM25 랭킹 (chat-memory-ranking.ts) + recency decay
   → 상위 K개 문서 + 요약 + 최근 이벤트 + 관계 상태 → 컨텍스트
5. 압축: compactMemoryDocumentsIfNeeded() → 50턴마다 documents.jsonl 압축
```

---

## 9. 일반 사용자 / 관리자 기능 구분

### 일반 사용자 (세션 쿠키 기반)

| 기능 | 구현 | 비고 |
|------|------|------|
| 채팅 | ChatLayout → /api/chat | 미인증 사용자도 가능 (게스트) |
| 회원가입/로그인 | AuthPanel → /api/auth/* | scrypt 비밀번호 해시 |
| 채팅방 저장/삭제 | /api/account/rooms | 로그인 필수 |
| 응답 스타일 (맛×길이) | ChatHeader → /api/account/response | 6가지 조합 |
| 커스텀 캐릭터 프롬프트 | CustomPromptDialog | 채팅방별 `$$slot$$` 대체 |
| 테마 변경 | ThemeSelector (로컬 스토리지) | 7개 테마 |
| 모델 선택 | ChatHeader → /api/models | 캐릭터 모델 오버라이드 |
| 턴 건너뛰기 | ChatInput skip 버튼 | AI만 응답 |
| 메모리 조회 | 없음 (자동) | buildMemoryContext()로 포함 |

### 관리자 (ADMIN_TOKEN Bearer 인증)

| 기능 | 구현 | 비고 |
|------|------|------|
| 챗봇 CRUD | /api/admin/chatbots | 캐릭터 추가/수정/삭제 |
| 모델 새로고침 | 관리자 페이지 RefreshCw 버튼 | LM Studio/Ollama 재검색 |
| DeepSeek API 키 | 관리자 페이지 → provider-settings.json | |
| 대화 로그 조회 | /api/admin/chats | 사용자별, 페이지네이션 |
| 프롬프트 편집 | /api/admin/prompts | 16개 섹션 + 커스텀 |
| 프롬프트 카테고리 | /api/admin/prompts (categories, assignments) | |

---

## 10. 인증 및 권한 구조

### 사용자 인증
```
lib/auth.ts
  ├── registerUser() → 이름+비밀번호 → scrypt 해시 → auth-users.json 저장
  ├── authenticateUser() → 비밀번호 검증 → 세션 토큰 → auth-sessions.json
  ├── getCurrentUser() → zeta_session 쿠키 → 세션 검증 → 사용자 조회
  └── 세션 쿠키: HttpOnly, SameSite=Lax, Max-Age=30일
```

### 관리자 인증
```
lib/admin-auth.ts
  ├── getAdminAuthError() → Authorization: Bearer 헤더 ↔ ADMIN_TOKEN 환경 변수
  └── 실패 시 401 또는 503 (ADMIN_TOKEN 미설정)
```

### 속도 제한
```
lib/rate-limit.ts
  ├── in-memory Map<"prefix:IP", {count, resetAt}> → 최대 5000 버킷
  ├── 각 엔드포인트별 prefix, maxRequests, windowMs 설정
  └── RATE_LIMIT_DISABLED=1 → 전체 비활성화
```

---

## 11. 개발, 빌드, 실행, 배포

### 로컬 개발

```bash
npm install            # 의존성 설치
npm run dev            # next dev → http://127.0.0.1:3000
npm run lint           # ESLint 검증
npm run build          # scripts/next-build.mjs → next build (BUILD_ID 보정)
npm run start          # next start (프로덕션 서버)
```

### 환경 변수 (.env.example 참조)

- `.env.example`이 템플릿. 실제 `.env` 또는 `.env.local`은 gitignore
- 주요 카테고리: AI 제공자, 모델 선택, 토큰 제한, 메모리 설정, 속도 제한, 관리자 토큰
- 프로덕션 환경 변수: `/etc/zeta-chat-ui-origin.env` (systemd 서비스)

### 배포 (Raspberry Pi)

```bash
sudo bash scripts/deploy-zeta-root.sh
```

이 스크립트가 수행하는 작업:
1. `npm run build` 실행
2. `/srv/zeta-next-ui/releases/{timestamp}/`에 배포
3. `/srv/zeta-next-ui/current` 심링크 갱신
4. systemd 서비스 `zeta-next-ui.service` 생성/갱신 (포트 3033)
5. Caddy Caddyfile `zeta.dcout.site` 블록 업데이트
6. Caddy 검증 후 reload
7. 서비스 헬스 체크 (HTTP 200)

### SSH 터널 (Windows → Raspberry Pi)

LM Studio/Ollama가 Windows PC에서 실행 중일 때:
- `scripts/lmstudio-reverse-tunnel.ps1` — LM Studio 터널 (포트 1234)
- `scripts/ollama-reverse-tunnel.ps1` — Ollama 터널 (포트 11434)
- `scripts/install-lmstudio-tunnel-task.ps1` — Windows 예약 작업으로 자동 재연결

---

## 12. 테스트 상태

- **테스트 파일 없음** — `__tests__/`, `*.test.ts`, `*.spec.ts` 모두 없음
- Playwright 1.61.1이 devDependencies에 설치되어 있으나, 테스트 스크립트 없음 [확인 필요: Playwright 사용 계획]
- `package.json`에 test 스크립트 없음
- 검증은 `npm run lint && npm run build`만 존재

---

## 13. 기술 부채와 정리 후보

### 즉시 조치 고려 대상

| 항목 | 상태 | 설명 |
|------|------|------|
| `pages/` 디렉토리 | **비어 있음** | Pages Router 미사용. 불필요한 디렉토리 |
| `node_modules_bak_20260630072725/` | **오래된 백업** | 6월자 node_modules 백업. 디스크 공간 낭비 |
| `.deploy-backups/` (5개 .tgz) | **누적된 백업** | 용량 확인 후 오래된 것 정리 |
| `.codex-backups/` (5개 디렉토리) | **Codex 작업 백업** | 프로젝트 코드와 무관 |
| `.codex-remote-attachments/` | **첨부 사진 1개** | 프로젝트 코드와 무관 |
| `tmp/` + `tmp/deploy-backups/` | **임시 파일** | gitignore 대상이나 정리 검토 |

### 설계 개선 후보

| 항목 | 설명 |
|------|------|
| `lib/mock-data.ts` | 이름이 "mock"이지만 production 기본값으로 사용. `default-data.ts` 등으로 개명 검토 |
| `lib/chat-memory.ts` (1567줄) | 프로젝트 최대 파일. 관심사 분리 검토 (상태, 검색, 관계, 압축) |
| `lib/chat-provider.ts` + `lib/runtime-models.ts` | 제공자 URL/모델 검색 책임이 두 파일에 분산 |
| `lib/chat-response.ts` | 스트림 리미터 + 응답 길이 계약 혼재 |
| 테스트 부재 | 모든 비즈니스 로직이 테스트 없음. 최소한 API 라우트 + 메모리 시스템에 테스트 권장 |
| Playwright 미사용 | 설치되어 있으나 활용 안 됨. 사용하거나 제거 |

---

## 14. 절대 임의 변경하면 안 되는 영역

### 데이터/운영

- `data/` 디렉토리 내용 — 런타임 사용자 데이터, 직접 수정 금지
- `.env` / `.env.local` / `env.production` — API 키, 토큰 포함
- `/var/lib/zeta-next-ui/data/` (프로덕션) — 운영 데이터
- `/srv/zeta-next-ui/current` (프로덕션) — 심링크 경로

### 코드 규칙

- `AGENTS.md`의 지침 따를 것 (경로, 명령)
- `.env` 값을 코드에 하드코딩하지 말 것
- SSH 비밀번호, API 키, 토큰을 코드나 문서에 저장하지 말 것
- `pages/`가 아닌 `app/` 디렉토리에 새 라우트 추가할 것 (App Router)
- 타입은 `types/chat.ts`에 추가할 것

### 배포

- `scripts/deploy-zeta-root.sh`의 Caddyfile 블록 교체 로직 — 문자열 정확히 일치해야 함
- systemd 서비스 파일 — `deploy-zeta-root.sh`가 자동 생성, 수동 수정 금지

---

## 15. 새 작업 시작 절차

1. `PROJECT_CONTEXT.md` (이 문서) 읽기
2. `docs/file-map.md` 읽기 — 수정이 필요한 파일 식별
3. `AGENTS.md` 읽기 — 프로젝트별 지침 확인
4. 타입 추가가 필요하면 `types/chat.ts` 먼저 수정
5. 새 API 라우트는 `app/api/` 아래에 추가 (App Router)
6. 새 컴포넌트는 `components/chat/` 또는 적절한 하위 디렉토리에 추가
7. 파일 I/O는 `server-files.ts`의 유틸 사용 (원자적 쓰기 보장)
8. 검증: `npm run lint && npm run build`
9. 커밋 전 `.env`, 데이터 파일, 백업 파일이 포함되지 않았는지 확인

---

*최종 확인일: 2026-08-05 (코드 기준)*
