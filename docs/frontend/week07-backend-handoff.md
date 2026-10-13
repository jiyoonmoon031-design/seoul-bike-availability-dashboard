# Week 07 Frontend → Backend Handoff

Frontend owner: Moon Jiyoon

## Frontend ready

The operator UI currently expects:

GET /api/v1/operator/rebalancing
  ?base_time=
  &horizon=
  &top_n=

GET /api/v1/stations/status

The station status adapter already matches the current backend DTO.

## Backend dependency

The following operator endpoints are not present in the current develop backend:

- GET /api/v1/operator/risk
- GET /api/v1/operator/rebalancing

Frontend currently uses MSW for these responses.

## Integration requirements

Backend integration owner should provide:

1. operator rebalancing endpoint
2. operator risk endpoint
3. station metadata/current inventory endpoint connectivity
4. frontend/backend error handling
5. localhost development connectivity or CORS/proxy policy

Frontend must not recompute shortage/surplus from bikes_now.

The Week 06 rebalancing result remains the authoritative source for:

- shortage_top
- surplus_top
- move_matches
- priority_score
- risk_time

Once backend integration is ready, frontend switches:

VITE_USE_MSW=false
VITE_API_BASE_URL=<backend URL>
