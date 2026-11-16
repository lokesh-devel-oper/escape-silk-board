# Escape Silk Board

## 1. Project introduction

Escape Silk Board is a production-minded, AI-assisted text adventure built around one rule: **code owns the facts; the LLM owns the story**. Python resolves every move and resource change. Gemini, when configured, interprets natural language and gives Ravi his voice without receiving authority over game state.

The application is complete locally and prepared for independent Netlify and Render deployment. No public URL is claimed because this repository has not been connected to deployment accounts.

## 2. Game concept

It is 7:00 PM at a fictionalized Bengaluru Silk Board junction. Your flight leaves at 9:40 PM, but check-in closes at 8:55 PM. You have ₹500, 32% phone battery, and one cold samosa. Reach Kempegowda International Airport before the counter closes while Ravi, a sarcastic local guide, comments on your decisions.

The travel values are deliberately fictional gameplay data, not live traffic or transit advice.

## 3. Gameplay rules

- Reach the airport at or before 8:55 PM. Arrival exactly at the deadline wins.
- A turn is accepted only when its preconditions are satisfied. Rejected actions do not spend time, cash, battery, or inventory.
- Travel is restricted to registered connections and transport modes.
- Cash and battery cannot fall below zero; battery cannot exceed 100%.
- The cold samosa can be traded only once.
- Seeded traffic events add either zero or two minutes, making a session reproducible.
- Reaching the airport after the deadline or exhausting the clock away from it loses the game.
- Finished sessions reject further gameplay actions; restart to try another strategy.

Safe bus, fast cab, and riskier metro/walking combinations all provide viable strategic paths.

## 4. Features

- Natural-language actions with Gemini structured interpretation and deterministic phrase fallback.
- Thirteen registered action types, eight locations, multiple transport modes, and explicit route preconditions.
- Versioned world metadata and destination-specific actions supplied entirely by FastAPI.
- Interactive suggestions expose travel time, cash, battery, disabled reasons, and explicit destinations.
- Authoritative time, cash, battery, inventory, map discovery, history, status, and character memory.
- Ravi narration generated after state resolution and screened for invented facts.
- Bounded AI timeouts, retries, confidence gating, and deterministic recovery.
- Isolated sessions, per-session concurrency locks, and idempotent action requests.
- Responsive React interface with a story timeline, map, resource cards, suggestions, and mobile command deck.
- Win, loss, restart, reload restoration, rejected-action, loading, and server-error states.
- Backend unit/API/AI tests, frontend component tests, and real-browser end-to-end gameplay tests.

## 5. Technology stack

| Layer | Technology |
|---|---|
| Game/API | Python 3.11+, uv, FastAPI, Pydantic v2, Uvicorn |
| AI | Google Gen AI SDK with Pydantic structured output |
| Client | React, TypeScript, Vite, Tailwind CSS, Lucide icons |
| Tests | pytest, HTTPX, Vitest, Testing Library, Playwright |
| Deployment | Render Blueprint for the API; Netlify config for the client |

## 6. Architecture

```text
React UI
   │ player text
   ▼
FastAPI ──► Gemini intent adapter ── timeout/invalid/low confidence ──┐
   │                                                               │
   └──────────────── deterministic phrase fallback ◄───────────────┘
                              │ ActionProposal (untrusted)
                              ▼
                  deterministic rules engine
                    │ routes, costs, checks
                    ▼
             authoritative state transition
                    │ resolved facts only
                    ▼
             Gemini narrative adapter ── unsafe/failure ──► deterministic narrator
                    │
                    ▼
          locked in-memory session store ──► typed API response ──► React UI
```

AI adapters are optional. Removing the API key changes language flexibility and prose variety, not the rules or playability.

## 7. Project folder structure

```text
backend/app/
  ai/                 Gemini clients, prompts, interpretation, narration
  config.py           bounded backend environment settings
  engine.py           deterministic state transitions
  main.py             FastAPI routes, CORS, health check
  models.py           request, response, state, and AI schemas
  store.py            sessions, locks, idempotency
  world.py            locations, actions, routes, seeded events
frontend/
  Dockerfile          Vite build and Nginx runtime image
  nginx.conf          SPA serving and same-origin API proxy
  e2e/                live browser gameplay specifications
  scripts/            isolated E2E service runner
  src/api/            typed API client
  src/components/     game interface components
  src/hooks/          session and action orchestration
  src/types/          frontend game contract
tests/                backend engine, API, AI, and safety tests
.env.example          backend environment template
netlify.toml          frontend build and SPA routing
render.yaml           backend service Blueprint
compose.yaml          complete Dockerized application stack
backend/Dockerfile    non-root uv/FastAPI runtime image
pyproject.toml        Python metadata and runtime/dev dependency groups
uv.lock               reproducible Python dependency lockfile
DESIGN.md             concise product decisions
```

## 8. Backend installation

From the repository root in PowerShell:

```powershell
uv sync --frozen
Copy-Item .env.example .env
```

Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/) are required. `uv sync --frozen` creates `.venv` and installs the locked runtime and development groups. Production uses `uv sync --frozen --no-dev`.

## 9. Frontend installation

Node.js 22 is the deployment target.

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
```

`npm install` honors the committed lockfile. Do not put a Gemini key in a `VITE_` variable because Vite variables are shipped to the browser.

## 10. Environment variables

| Variable | Location | Default | Purpose |
|---|---|---:|---|
| `ALLOWED_ORIGINS` | Backend | Both `localhost:5173` and `127.0.0.1:5173` | Comma-separated exact client origins |
| `GEMINI_API_KEY` | Backend | unset | Secret Gemini credential |
| `GEMINI_MODEL` | Backend | unset | Explicit supported Gemini model ID |
| `GEMINI_TIMEOUT_SECONDS` | Backend | `5` | Per-attempt wall-clock limit, clamped to 0.5–30 |
| `GEMINI_MAX_RETRIES` | Backend | `1` | Retries after the first attempt, clamped to 0–2 |
| `GEMINI_MIN_CONFIDENCE` | Backend | `0.55` | Intent proposals below this use fallback |
| `VITE_DEV_API_TARGET` | Vite development server | `http://127.0.0.1:8000` | Backend target for the same-origin local proxy |
| `VITE_API_BASE_URL` | Frontend production build | unset | Public backend origin, without a trailing slash |
| `VITE_BASE_PATH` | Frontend build | `/` locally, `/gameplay/` in Docker | Public URL prefix used by assets and same-origin API calls |
| `APP_PORT` | Docker Compose | `18080` | Host port for the complete containerized application |
| `DOCKER_ALLOWED_ORIGINS` | Docker backend | Local port 18080 origins | Exact direct-access origins inside the Docker deployment |

FastAPI itself does not automatically read `.env`; the local Uvicorn command below loads it explicitly. A shell, IDE, or hosting dashboard can supply the same values. The example files are safe templates and contain no secret.

## 11. Gemini API setup

Create an API key in Google AI Studio, choose a model currently supported by the Google Gen AI SDK, and set both backend values:

```powershell
$env:GEMINI_API_KEY = "your-secret-key"
$env:GEMINI_MODEL = "your-supported-model-id"
```

If either value is absent, both AI layers use deterministic fallbacks. The key remains server-side and is never included in the player prompt, API response, frontend bundle, or application log. Consult the [Gemini model documentation](https://ai.google.dev/gemini-api/docs/models) before selecting a model.

## 12. Local execution

Start the API from the repository root:

```powershell
uv run --frozen uvicorn backend.app.main:app --reload --env-file .env
```

Start the client from a second terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. In development, the browser calls same-origin `/api` paths and Vite proxies them to `VITE_DEV_API_TARGET`, avoiding browser CORS entirely. The default API is at `http://127.0.0.1:8000`, with documentation at `/docs` and health at `/health`.

### Dockerized full stack

Docker Compose builds two production images. Nginx serves the compiled React application and proxies `/api`, `/health`, `/docs`, and `/openapi.json` to the private FastAPI container. The backend uses the committed uv lockfile, excludes development packages, and runs as a non-root user.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Open `http://localhost:18080/gameplay/`; API documentation is available through the same prefix at `http://localhost:18080/gameplay/docs`. The Docker image builds Vite with `VITE_BASE_PATH=/gameplay/`, and Nginx strips that prefix before serving assets or proxying FastAPI. Change `APP_PORT` and the matching `DOCKER_ALLOWED_ORIGINS` entries in `.env` if that port is occupied.

Useful lifecycle commands:

```powershell
docker compose logs -f
docker compose down
docker compose build --no-cache
```

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the uncommitted root `.env` to enable Gemini inside the backend container. Leaving both blank retains deterministic mode. Session data remains in process memory and is lost when the backend container is recreated.

## 13. API endpoints

| Method | Path | Request | Success response |
|---|---|---|---|
| `GET` | `/health` | none | Service status |
| `GET` | `/api/world` | none | Versioned locations, routes, actions, labels, and map metadata |
| `POST` | `/api/game/new` | `player_name`, optional `random_seed` | `201` with `GameState` |
| `POST` | `/api/game/action` | `session_id`, `player_input`, unique `request_id` | `ActionResult` |
| `GET` | `/api/game/state/{session_id}` | path ID | `GameState` snapshot |
| `GET` | `/api/game/context/{session_id}` | path ID | State plus structured available actions |
| `POST` | `/api/game/reset/{session_id}` | path ID | Reset `GameState` using the original seed |

Unknown sessions return `404`. Reusing a request ID with different input returns `409`; reusing it with the same input returns the cached result with `duplicate: true`. Validation errors return `422`.

```powershell
$game = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/game/new `
  -ContentType application/json -Body '{"player_name":"Maya","random_seed":42}'

$action = @{
  session_id = $game.session_id
  player_input = "Take the airport bus"
  request_id = [guid]::NewGuid().ToString()
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/game/action `
  -ContentType application/json -Body $action
```

## 14. Game-state design

`GameState` is the single authoritative snapshot. It contains identity (`session_id`, `player_name`, `random_seed`), clocks, location, cash, battery, inventory, turn/status fields, history, discovered locations, character memory, narrative, and last action. Pydantic validates resource bounds on creation and assignment.

`ActionResult` adds acceptance, an action ID, exact deltas, structured destination-aware suggestions, duplicate status, and separate intent/narration metadata. `WorldDefinition` supplies all route, label, action, and map presentation data used by React. Time is stored as integer minutes since midnight to avoid ambiguous string arithmetic. State returned by the store is copied so callers cannot mutate a live session.

## 15. Deterministic game engine

Actions and routes are data-driven registries. An interpreted action is only a proposal: the engine looks up the applicable definition, resolves an explicit destination, checks location, route, cash, battery, inventory, status, and NPC memory, then applies a transition to a copy. Ambiguous travel requests return valid destination choices instead of selecting the first registered route. The copy is validated before it replaces the session state.

Seeded event selection keeps variation reproducible. Win/loss evaluation runs after the transition, and deterministic outcome text always leads the final message. This makes rules testable without Gemini and prevents generated text from changing facts.

## 16. LLM architecture

The intent prompt sends quoted JSON context and requests a strict `ActionProposal` containing only an action type, optional target, confidence, and short reason. Unknown actions, extra fields, malformed output, low confidence, provider errors, and timeouts fall back safely.

Narration is a second, post-transition call. It receives resolved facts, recent history, structured Ravi memory, and an urgency band. Its `NarrativeProposal` may only contain a scene and Ravi line. A guard rejects digits, resource/terminal claims, non-current locations, repeated lines, or other factual conflicts and substitutes deterministic prose.

## 17. Testing

Run backend tests from the repository root:

```powershell
uv run --frozen pytest -q
```

Run frontend component tests, a production build, and live E2E tests:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
```

The E2E runner starts isolated FastAPI and Vite processes on ports 8765 and 4173, exercises the real HTTP/CORS boundary in Microsoft Edge, and cleans them up. Coverage includes bus/cab/metro wins, a loss, reload, restart, prompt injection, rapid duplicate submission, and a 390-pixel viewport.

The last local verification produced 90 passing backend tests, 4 passing component tests, and 7 passing browser tests. Live Gemini calls were not made because no credential was supplied; controlled clients cover success and failure behavior.

## 18. Frontend deployment (Netlify)

1. Push the repository to a Git provider and create a Netlify site from it.
2. Netlify reads root `netlify.toml`, sets `frontend` as the base, runs `npm run build`, and publishes `frontend/dist`.
3. In Netlify environment variables, set `VITE_API_BASE_URL` to the deployed Render origin, for example `https://your-api.onrender.com`.
   Keep `VITE_BASE_PATH=/` when Netlify serves this application at the domain root.
4. Deploy again after changing a `VITE_` value because it is embedded at build time.
5. Copy the final Netlify origin into Render's `ALLOWED_ORIGINS` and redeploy the backend.
6. Open the site, start a game, make a move, reload, and finish one route. Check browser network requests and mobile layout.

The SPA redirect in `netlify.toml` makes future client-side routes resolve to `index.html`.

## 19. Backend deployment (Render)

1. Push the repository and create a Render Blueprint using root `render.yaml`.
2. Supply `ALLOWED_ORIGINS` as the exact Netlify origin, `GEMINI_API_KEY` as a secret, and `GEMINI_MODEL` as the selected model. Gemini values may be left blank for deterministic-only play.
3. Render detects `uv.lock`, runs `uv sync --frozen --no-dev`, and starts `uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
4. Confirm `/health` returns `{"status":"ok","service":"escape-silk-board-api"}`.
5. Confirm `/docs`, create/action/state/reset calls, CORS from Netlify, and a complete win or loss.

Run exactly one process/instance with the current in-memory store. Multiple workers do not share sessions. `.python-version` pins the Python 3.13 line; change it deliberately and rerun all tests before upgrading.

## 20. Troubleshooting

| Symptom | Check |
|---|---|
| Browser says server is unreachable locally | API is running and `VITE_DEV_API_TARGET` contains its exact origin with no `/api` suffix |
| Production CORS error | `VITE_API_BASE_URL` points to Render and `ALLOWED_ORIGINS` contains the exact Netlify origin |
| AI always reports deterministic | Both `GEMINI_API_KEY` and `GEMINI_MODEL` must be set on the backend |
| AI timeout/provider fallback | Verify quota/model access; increase the bounded timeout only when needed |
| Session disappears | A restart or a different worker lost in-memory data; use one instance |
| Action returns `409` | Generate a new `request_id`, or retry the original ID with identical input |
| Netlify still calls localhost | Set `VITE_API_BASE_URL` and trigger a new frontend build |
| E2E cannot launch | Install Microsoft Edge or adjust the Playwright project/browser channel |

## 21. Security considerations

- Secrets are backend-only, absent from templates, and represented as `sync: false` in the Render Blueprint.
- CORS accepts exact configured origins, limited methods, and only the content-type request header.
- Request lengths and model schemas are bounded; extra AI fields are forbidden.
- Player text is JSON-quoted and explicitly treated as untrusted data in prompts.
- LLM proposals cannot write state. Engine preconditions and Pydantic validation remain authoritative.
- Timeouts and retry caps limit provider stalls and runaway requests.
- Narrative safety checks prevent generated resource, location, and terminal-state claims.
- Production should add rate limiting, durable storage, retention policy, observability, and dependency scanning before handling significant traffic.

## 22. Current limitations

- Sessions and idempotency records are process-local and disappear on restart.
- Horizontal scaling and multiple Uvicorn workers are unsafe until a shared store is added.
- The fallback interpreter recognizes registered aliases rather than arbitrary semantic paraphrases.
- A configured accepted turn can make two model requests: intent and narration.
- Traffic, routes, and prices are fictional and static.
- The world is API-driven and has no duplicated frontend route tables, but the current backend registry is not yet procedurally generated per session.
- Browser automation currently targets the installed Microsoft Edge channel.
- Live Gemini behavior and a public deployment have not been manually verified without credentials/accounts.

## 23. Future enhancements

- Redis or a database for durable sessions, distributed locking, and idempotency.
- Authentication, saved runs, leaderboards, and privacy-aware retention controls.
- Rate limits, structured telemetry, alerting, and provider/cost dashboards.
- More locations, NPC arcs, achievements, accessibility audits, and localization.
- CI for backend, frontend, build, and Playwright checks on every change.
- Provider evaluation datasets for intent accuracy and narrative safety regressions.

## 24. Example gameplay

```text
Player: Find me an auto.
Game: An auto driver quotes a direct airport fare. 2 minutes pass.
Ravi: Silk Board pricing has discovered venture capital, apparently.

Player: Negotiate with the driver.
Game: The driver lowers the fare. 3 minutes pass.

Player: Take the cab to the airport.
Game: The registered fare, battery use, traffic event, and travel time are applied.
Ravi: You made it. I will pretend this was the plan all along.
```

Exact narrative wording can vary; the engine's deltas and terminal result do not.

## 25. Cost estimation methodology

No monetary estimate is asserted because traffic, selected Gemini model, token counts, hosting plans, and current provider prices are not fixed. Estimate deployment cost from measurable usage:

```text
monthly AI requests = completed turns × AI calls per turn
monthly input cost  = input tokens ÷ 1,000,000 × current input rate
monthly output cost = output tokens ÷ 1,000,000 × current output rate
monthly total       = input cost + output cost + Render plan + Netlify usage/plan
```

An accepted AI-enabled turn normally uses one intent call and one narration call; deterministic fallbacks and idempotent duplicate retries avoid additional successful model work where possible. Measure real input/output tokens and request counts, separate free-tier assumptions from paid rates, add expected retry/error traffic, and use the providers' current pricing pages at estimation time.
