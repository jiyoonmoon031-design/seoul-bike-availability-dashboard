# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Week 07 Operator Dashboard

The Week 07 operator dashboard adds:

- base time control
- 15 / 30 / 60 minute prediction horizon
- Top N selection
- shortage / surplus / normal station visualization
- Kakao Map station markers
- station detail popup
- rebalancing movement lines and quantities
- rebalancing priority table
- TanStack Query API layer
- MSW mock operator API
- StationStatus backend DTO adapter
- loading / error / retry states
- baseline fallback indicator

The map and route functionality previously merged into `develop`
is retained. Shared frontend dependencies use the latest `develop`
versions.

### Operator API status

Until the backend operator endpoints are available:

    VITE_USE_MSW=true

When backend integration is ready:

    VITE_USE_MSW=false
    VITE_API_BASE_URL=<backend URL>

The frontend does not recompute shortage or surplus status from
current inventory. Week 06 rebalancing output remains the
authoritative source for shortage, surplus, priority, and movement
matching.
