# API reference

All API routes are mounted under `/api` unless otherwise noted. FastAPI also
serves generated OpenAPI docs at `/docs`.

## Health

- `GET /health`
- `GET /api/health`

Response:

```json
{"ok": true}
```

## Metadata

- `GET /api/subjects`
- `GET /api/textbooks`
- `GET /api/units`
- `GET /api/problem-formats`
- `GET /api/units/{unit_id}/allowed-formats`

These endpoints return seed and user metadata only. They must not include
copied textbook body text or copyrighted problems.

`GET /api/units` supports `subject_id`, `grade_label`, and `semester_label`
filters. Unit responses include `semester_label` and curriculum area metadata.

## AI provider

- `GET /api/ai/status`
- `POST /api/ai/test`

`/api/ai/status` returns provider availability, key counts, cooldown counts, and
default model name. It never returns key secrets.

`/api/ai/test` sends a small structured-output request when Gemini keys are
configured. Without keys it returns a safe unavailable error and does not crash
the app.

## Planning

- `POST /api/generation/plan`

Request fields:

- `subject_id`
- `textbook_id`
- `unit_id`
- `difficulty_level`
- `requested_count`
- `generation_mode`
- `selected_format_codes`
- `format_weights`
- `generation_instruction`
- `random_seed`
- `explanation_style`
- `include_answers`

Supported `generation_mode` values:

- `selected`
- `random`
- `mixed_random`
- `instruction_guided`

The response contains `problem_slots` with slot index, format code, difficulty,
validation method, rendering type, and planning reason.

## Generation

- `POST /api/generate`
- `POST /api/generation/create`
- `GET /api/problem-sets`
- `GET /api/problem-sets/{id}`
- `GET /api/problem-sets/{id}/logs`
- `DELETE /api/problem-sets/{id}`
- `GET /api/problems`
- `GET /api/problems/{id}`

`POST /api/generate` creates a problem set, builds a plan, calls the AI provider
one slot at a time, saves problems, and writes generation logs. `POST
/api/generation/create` is the Android-friendly wrapper that returns
`problem_set_id`, `requested_count`, `generated_count`, `problems`, `warnings`,
and `errors`. Both are limited by `MAX_PROBLEMS_PER_GENERATION`.

`GET /api/problem-sets` supports `limit`, `offset`, `status`, and `unit_id`.
`GET /api/problems` supports `limit`, `offset`, `problem_set_id`,
`validation_status`, and `format_code`.

If Gemini keys are not configured, `/api/generation/create` returns a 503
response with `available=false` and does not create a problem set.

Problem set statuses:

- `planned`
- `generating`
- `generated`
- `partially_failed`
- `failed`

Problem validation statuses used after generation:

- `pending_validation`
- `needs_review`
- `generation_failed`

## Validation

- `POST /api/validate/problem/{problem_id}`
- `POST /api/validate/problem-set/{problem_set_id}`

Validation returns a stored `validation_results` row. Supported final statuses
include:

- `auto_validated`
- `validation_failed`
- `needs_review`
- `manual_review_required`
- `validation_error`
- `unsupported`

## Rendering

- `POST /api/problems/{id}/render`
- `POST /api/problem-sets/{id}/render`
- `GET /rendered/{filename}` outside `/api`

Supported rendering types:

- `none`
- `html_table`
- `graph_svg`
- `coordinate_svg`
- `geometry_svg`

SVG outputs are cached under `data/rendered/`. Table HTML is returned in the
rendered asset payload. Path traversal is rejected by the static file mount and
renderer filename checks.

## Web pages

These routes are server-rendered HTML:

- `GET /`
- `POST /generate`
- `GET /problem-sets/{id}`
- `GET /problem-sets/{id}/worksheet`
- `GET /problem-sets/{id}/answers`
- `POST /problem-sets/{id}/validate`
- `POST /problem-sets/{id}/render`
