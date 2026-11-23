# Features

One folder per area of the product, following
[bulletproof-react](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md).
A feature holds the code for its area. Its pages live in `src/app/routes`,
which put features together.

```
features/projects/
  api/          Requests and query hooks: get-projects.ts, apply-to-project.ts
  components/   Components only this feature uses: project-card.tsx
  hooks/        Hooks only this feature uses
  types/        Types only this feature uses
  utils/        Helpers only this feature uses
```

Only add the folders a feature needs.

Expected features and the issues that start them:

| Folder         | What it covers                                                                                                                          | Issues                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `projects`     | Project list and details, applying                                                                                                      | #236                   |
| `applications` | Applications and their status labels; a team's agree, decline, withdraw; supervisor accept or decline; course staff's approve or reject | #237, #238, #239, #240 |
| `teams`        | Teams and their members                                                                                                                 | #240                   |
| `demo`         | Demo reset and the consistency checks                                                                                                   | #242                   |

Rules (ESLint checks the first two):

- A feature can import shared code (`@/components`, `@/lib`, `@/config`,
  ...) but not `@/app`.
- A feature shouldn't import another feature. If a page needs two, the page
  in `src/app/routes` imports both. Add a zone for the new feature in
  `eslint.config.js` so this is checked.
- Import files directly, not through an `index.ts` that re-exports a whole
  feature. Re-exporting gets in the way of Vite removing unused code.
