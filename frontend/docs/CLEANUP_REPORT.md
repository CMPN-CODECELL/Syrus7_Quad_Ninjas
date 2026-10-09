# Frontend Cleanup Report

**Date:** 2026-10-09  
**Scope:** `frontend/` only. No backend files were moved or modified as part of this cleanup.

## Original Inventory

Outside generated/dependency folders, the frontend initially contained:

```text
frontend/
  index.html
  package.json
  package-lock.json
  src/
    main.jsx
    style.css
  dist/                 generated Vite production output
  node_modules/         installed dependencies
```

The original `src/main.jsx` implemented the shell, all five page views, API requests, shared state, charts, and small reusable view components in one file. `src/style.css` was its sole global stylesheet. `index.html` referenced `/src/main.jsx`; `package.json` scripts call Vite. No router, custom hooks, state context, TypeScript declarations, local image/icon assets, frontend tests, lint config, or frontend-specific docs existed.

## Organized Source Structure

```text
frontend/
  Delete/                         empty quarantine directory; no files were safe to move
  docs/
    CLEANUP_REPORT.md
  src/
    app/
      App.jsx                     shared state, API orchestration, navigation shell
    components/
      charts/
        HospitalCharts.jsx        shared forecast and staff donut charts
      ui/
        HospitalComponents.jsx    shared stat, section, progress, diagnostic, range, flow components
    constants/
      dashboard.js                five navigation items, icons, chart colors
    pages/
      OperationsDashboard.jsx
      ResourceCapacity.jsx
      BottleneckPrediction.jsx
      PatientFlow.jsx
      ScenarioLab.jsx
    services/
      api.js                      shared fetch helper and configurable API base URL
    utils/
      hospital.js                 date/time formatting and risk lookup
    main.jsx                      Vite React mount
    style.css                     existing global dashboard stylesheet
  index.html
  package.json
  package-lock.json
  dist/                           preserved generated build output
  node_modules/                   preserved installed dependencies
```

## Files Moved

Original pages and shared implementation were colocated in `frontend/src/main.jsx`; the initial Vite file now only mounts `src/app/App.jsx` and imports the existing stylesheet. Extracted modules are listed below. The original `style.css` is intentionally kept at its same path because it is globally imported by the Vite entry and contains all shared page styling; relocating it offered no safety or maintenance benefit in this small project.

| Responsibility | Destination |
|---|---|
| App shell, API orchestration, shared state and handlers | `src/app/App.jsx` |
| Operations Dashboard view | `src/pages/OperationsDashboard.jsx` |
| Resource & Capacity Management view | `src/pages/ResourceCapacity.jsx` |
| Bottleneck Prediction view | `src/pages/BottleneckPrediction.jsx` |
| Patient Flow view | `src/pages/PatientFlow.jsx` |
| AI Recommendations & Scenario Lab view | `src/pages/ScenarioLab.jsx` |
| Shared chart components | `src/components/charts/HospitalCharts.jsx` |
| Shared UI components | `src/components/ui/HospitalComponents.jsx` |
| API fetch helper | `src/services/api.js` |
| Navigation and chart palette | `src/constants/dashboard.js` |
| Time formatting and risk lookup | `src/utils/hospital.js` |

## Renamed Files

No files were renamed for cosmetic reasons. `main.jsx` remains at its existing Vite entry path to avoid changing `index.html` or build configuration.

## Duplicate Code Consolidated

- The shared stat card, section header, progress bar, diagnostic card, slider, flow node, arrival forecast chart, and staff donut were moved into reusable components.
- Navigation metadata and chart colors now have one constants module.
- API requests now use one shared fetch helper without changing paths, HTTP methods, payloads, or response expectations.
- Time formatting and bottleneck lookup now have one utility module.

No page views or backend data behavior were removed.

## Quarantined Files

No files were moved into `Delete/`. The directory is empty because the inventory found no confirmed unused or duplicate source/assets.

Per-file quarantine records: none.

## Files Intentionally Preserved

- `package.json` and `package-lock.json`: required dependency/script manifests.
- `index.html`: required Vite document shell, still loads `/src/main.jsx`.
- `src/style.css`: active global stylesheet imported by `main.jsx`; preserved at its existing path.
- `dist/`: generated production output; preserved and refreshed by build verification.
- `node_modules/`: installed dependencies; preserved.
- No Vite, TypeScript, ESLint, test-runner, or environment-example config was present; none was invented.

## Potentially Unused Files Requiring Manual Review

None found in the source inventory. `dist/` is generated and should be governed by repository ignore/release policy, but it was preserved because no `.gitignore` or Git history was available for this workspace.

## Git and Recovery

The workspace has no `.git` directory and the shell does not provide a Git executable. A cleanup branch or Git-based restoration point could not be created. Existing source files were preserved or relocated into active frontend modules; no uncertain file was deleted or quarantined.

## Known Risks

- No TypeScript, test runner, or lint script is configured.
- API endpoints and payloads were intentionally unchanged.
- The active configured backend URL defaults to `http://localhost:8000`; runtime connectivity depends on that service being the current backend implementation.
- Vite continues to report the existing JavaScript bundle-size warning (>500 kB minified).

## Verification Results

- `npm run build`: passed after the module split (Vite 6.4.4; 2,201 modules transformed). The build emits the existing large-chunk warning.
- Frontend diagnostics: checked after migration; no errors reported.
- Browser checks on the existing Vite preview at `http://localhost:5174`: the refactored dashboard rendered with API data; the Resource & Capacity page rendered; the ICU selector updated bed values (20 occupied, 0 available, 24 physical, 4 temporarily unavailable); and the Scenario Lab page rendered after navigation.
- A Run Simulation interaction was attempted after migration but could not be reliably activated by the browser automation following page navigation. It is not claimed as post-cleanup verified. The backend was not changed.
- A temporary preview on port 5175 was not used for interaction verification because API 8001 CORS permits 5173/5174, not 5175; that temporary server was stopped. No backend CORS changes were made.
