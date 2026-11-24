# Security and reliability validation

Audit date: 2026-11-25 KST

## Implemented

- OpenAI remains AI-service-only; Backend and Frontend do not read its key.
- Seoul, Kakao REST, TMAP and database values remain Backend environment
  variables. No secret value was added to Git.
- Central CORS origins are configurable and production examples contain only
  the HTTPS application origin.
- Production LLM endpoints support constant-time shared-token validation at the
  trusted proxy/backend boundary, 64 KiB request limits and per-client minute
  limits. The token is never intended for frontend JavaScript.
- Prediction/candidate/question list and string sizes are bounded.
- Existing prompts treat user-provided strings as data, prohibit invented
  values, and validate structured LLM output. LLM failure preserves the base
  recommendation/rebalancing UI.
- TMAP uses connection/read timeouts and logs only the exception type before an
  explicit straight-line fallback; the key is never logged.
- Deployment templates bind AI and Backend to loopback and do not expose MySQL.
- Tests cover missing/valid LLM token, oversized requests and rate limiting.

## Verified

- `pre-commit --all-files`: pass, including private-key detection.
- Python tests: 94 pass.
- Backend Gradle tests: pass after the security changes.
- Frontend ESLint, TypeScript and production build: pass.
- `pip-audit` for both requirement files: no known vulnerabilities.
- `npm audit`: initially reproduced three moderate `minimatch` development
  dependency findings; `npm audit fix` updated the lockfile, and the final audit
  reports zero vulnerabilities. Lint, TypeScript, build and 7 Playwright tests
  passed again after the update.
- `.env*`, local files, logs, model artifacts and build outputs are ignored.

## Blocked or external

- `OPENAI_API_KEY` and `TMAP_API_KEY` were not present in this execution
  environment, so live provider authorization/timeout and cost measurements
  were not repeated.
- The known live TMAP result remains HTTP 403 `INVALID_API_KEY`; valid product
  entitlement must be confirmed in the SK Open API console. Real road geometry
  is not marked complete.
- Kakao JavaScript allowed-domain settings require console access and cannot be
  inferred from the key.
- EC2 Security Group, HTTPS certificate and external port checks require EC2
  access and reviewer approval.
- In-memory rate limits are per Backend process. A shared gateway/distributed
  limiter is required if production runs multiple Backend instances.
