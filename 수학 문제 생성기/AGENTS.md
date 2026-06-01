# AGENTS.md - mathgen-web

## 역할

Codex는 이 프로젝트의 구현 담당자다. 작업은 `구조 확인 -> 문서 확인 -> 최소 수정 -> 검증 -> 결과 보고` 순서로 진행한다.

## 프로젝트 목표

- Raspberry Pi에서 FastAPI 기반 수학 문제 생성 웹앱을 실행한다.
- 운영 도메인 목표는 `math.dcout.site`다.
- 초기 대상은 중학교 수학이며, 이후 Android 앱과 여러 과목을 붙일 수 있게 API-first 구조를 유지한다.
- 화면은 Jinja2 서버 렌더링과 정적 CSS 중심으로 단순하게 유지한다.

## 장기 기술 원칙

- 백엔드는 FastAPI를 사용한다.
- DB는 SQLite를 기본으로 사용한다.
- DB 접근은 SQLAlchemy 기반으로 유지한다.
- React, Vue, Node 빌드 시스템은 명시 요청 없이는 추가하지 않는다.
- Android 앱은 나중에 만들지만 `/api/*`가 같은 데이터를 안정적으로 제공해야 한다.
- 과목 확장은 `subjects`, `textbooks`, `units`, `problem_formats` 메타데이터 추가로 처리할 수 있게 유지한다.

## 보안/저작권 원칙

- 실제 API 키, 토큰, 비밀번호, `.env` 파일은 절대 커밋하지 않는다.
- `.env.example`에는 빈 값과 예시 설정만 둔다.
- 교과서 본문, 교과서 문항, 출판사 저작권 콘텐츠를 복사하거나 크롤링하지 않는다.
- 저장 가능한 것은 교과서/출판사/학년/단원/학습목표/허용 문제형식 같은 메타데이터뿐이다.
- 생성 프롬프트에는 실제 교과서 문항을 베끼지 말라는 조건을 유지한다.

## AI/생성 원칙

- Gemini 무료 API를 기본 provider로 사용한다.
- 여러 Gemini API 키 round-robin과 cooldown 구조를 유지한다.
- DeepSeek 같은 fallback provider는 인터페이스를 통해 나중에 붙일 수 있게 한다.
- Gemini 응답은 structured JSON으로 받으며 자유 텍스트 파싱에 의존하지 않는다.
- API 키가 없어도 앱이 죽으면 안 된다.
- 생성 실패는 앱 오류로 죽이지 말고 `generation_failed` 또는 `needs_review` 상태로 저장한다.

## 검증/렌더링 원칙

- 문제 정답은 AI만 믿지 않는다.
- 가능한 경우 bounded Python/SymPy 검증을 사용한다.
- 서술형/증명형은 자동 채점하지 말고 rubric 또는 manual review 상태로 둔다.
- 모든 검증은 timeout과 복잡도 제한을 고려한다.
- 검증 실패 문제도 삭제하지 않고 상태와 메시지를 저장한다.
- AI 이미지 생성은 금지한다.
- 그래프, 표, 좌표평면, 간단 도형은 SVG, HTML table 같은 deterministic rendering만 사용한다.
- 렌더링 실패도 앱 오류로 죽이지 말고 `render_failed` 상태로 저장한다.

## Raspberry Pi 저부하 원칙

- 기본 생성 수는 5~10문제 수준으로 제한한다.
- `MAX_PROBLEMS_PER_GENERATION`, `VALIDATION_TIMEOUT_SECONDS` 설정을 존중한다.
- 복잡한 SymPy 탐색, 대량 고해상도 이미지 생성, 무제한 재시도는 금지한다.
- 렌더링 결과는 캐싱한다.
- 대량 생성은 나중에 큐 구조로 분리한다.

## 배포 원칙

- Raspberry Pi 프로젝트 변경은 가능하면 Raspberry Pi 복사본에서도 검증한다.
- systemd/Caddy 같은 운영 설정 변경 전에는 백업과 롤백 경로를 준비한다.
- 사용자가 문서화만 요구한 단계에서는 실제 `/etc/systemd`, `/etc/caddy`를 변경하지 않는다.
- Caddyfile 전체를 덮어쓰지 말고 필요한 site block만 문서화/추가한다.

## 완료 보고

작업 완료 시 다음 항목을 보고한다.

- 변경 파일 목록
- 구현 완료 기능
- 미완료/후순위 기능
- 실행 명령
- 테스트 결과
- 배포 시 해야 할 작업
- 알려진 제한사항
- 추천 commit message
