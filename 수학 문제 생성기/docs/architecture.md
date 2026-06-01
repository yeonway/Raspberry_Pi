# mathgen-web architecture

## Scope

mathgen-web is a low-load FastAPI web app for Raspberry Pi. The first client is
a server-rendered web UI, but the backend is API-first so Android and additional
subjects can reuse the same data model and endpoints.

## Application layout

- `app/main.py`: FastAPI app factory, startup DB initialization, static mounts
- `app/routes/web.py`: Jinja2 web pages and form submissions
- `app/routes/api.py`: JSON API for metadata, planning, generation, validation, rendering
- `app/database.py`: SQLAlchemy engine/session helpers
- `app/models.py`: SQLAlchemy table models
- `app/seed.py`: idempotent seed metadata
- `app/services/ai/`: provider abstraction, Gemini provider, key pool, schemas
- `app/services/validators/`: bounded automatic validators
- `app/services/renderers/`: deterministic SVG/table renderers

## Data model

The metadata hierarchy supports:

`subject -> textbook -> grade -> unit -> subunit -> problem_format`

The current seed contains sample metadata only:

- one subject: math
- sample textbook metadata
- middle school units and learning goals
- allowed problem formats by unit

The app does not store copied textbook body text or copyrighted problem text.

Generation data is stored in:

- `problem_sets`
- `problems`
- `generation_logs`
- `validation_results`
- `rendered_assets`

## Generation

`GenerationPlanner` builds problem slots without calling AI. It supports:

- `selected`
- `random`
- `mixed_random`
- `instruction_guided`

The planner filters by unit-allowed formats and difficulty. `random_seed`
produces reproducible plans.

`GenerationService` creates a problem set, calls the provider one slot at a
time, saves structured JSON into `problems`, and records `generation_logs`.
Provider failures and invalid JSON responses are saved as failed problem rows
instead of crashing the app.

The API exposes two generation entrypoints:

- `POST /api/generate`: direct problem-set detail response for the existing web/API flow
- `POST /api/generation/create`: Android-friendly summary response with counts,
  warnings, errors, and saved problems

`GET /api/problem-sets` returns recent saved problem sets, and
`GET /api/problem-sets/{id}` returns a problem set with its problems.

## AI provider

`AIProvider` defines `generate_structured(prompt, schema, model_name, temperature)`.
The current concrete provider is Gemini.

Gemini API keys are loaded from environment variables and kept in an in-memory
round-robin key pool. Rate-limit, quota, and transient service failures mark a
key as cooldown and retry another key within the configured retry limit. The
provider interface is intentionally small so another provider can be added later.

No API response or generation log should expose the key secret.

## Validation

Validators are deliberately bounded for Raspberry Pi:

- arithmetic
- linear equation
- two-variable linear system
- function value
- multiple choice consistency
- graph payload data
- table interpretation
- rubric/manual review

Complex symbolic search, high-degree equations, matrices, calculus, and long
expressions are rejected as unsupported or validation errors. Results are stored
in `validation_results`, and the latest status/message is copied to `problems`.

## Rendering

Rendering is deterministic. AI image generation is not used.

Supported MVP renderers:

- `graph_svg`
- `coordinate_svg`
- `html_table`
- `geometry_svg`

SVG files are cached in `data/rendered/`, HTML tables are cached in
`rendered_assets.content_html`, and failed renders are saved as `render_failed`.

## Web UI

The web UI is intentionally small:

- home generation form
- problem set result page
- validate/render buttons
- worksheet print page
- answer sheet print page

The API remains the source of truth for Android and future clients.

## Deployment

Deployment artifacts live in `deploy/` and docs live in:

- `docs/deploy_raspberry_pi.md`
- `docs/operations.md`

Production target:

- `/opt/mathgen`
- `mathgen.service`
- `127.0.0.1:8020`
- `math.dcout.site`
- `/opt/mathgen/data/mathgen.sqlite3`

Actual systemd/Caddy changes should be made only during a deployment task with
rollback awareness.
