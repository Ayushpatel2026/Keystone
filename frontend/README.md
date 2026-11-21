# Keystone frontend

The web app for Keystone, built with React, TypeScript and Vite. It talks to
the FastAPI backend in [`../backend`](../backend).

## Running it

You need:

- **Node 26.** The version is in `.nvmrc`; with fnm or nvm, run `fnm use` or
  `nvm use` in this folder.
- **uv**, the same one the backend uses. The frontend's API types are
  generated from the backend's code, so `npm run dev` calls into it.
- **The backend running** on `localhost:8000`, to see real data. With Docker
  running and a `backend/.env` file (database settings and
  `KEYSTONE_SECRET_KEY`), run this in `backend`:

  ```powershell
  docker compose up -d --wait
  uv run alembic upgrade head
  uv run python -m app.core.seed
  uv run uvicorn app.main:app --reload --port 8000
  ```

  The middle two are only needed the first time, and after pulling new
  migrations.

Then, in this folder:

```powershell
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` and `/auth`
requests to the backend, so the browser sees one origin and there's no CORS
setup. If the backend runs somewhere else, set `KEYSTONE_API_URL` before
`npm run dev`.

### Picking a user

The proof of concept has no real sign-in. Use **Acting as** at the bottom of
the side menu (or the top of the menu on phones) to pick a seeded user. The
app signs in as them with the seed password behind the scenes, and every API
request then carries their token.

## Pages and roles

Each role gets its own menu, and `/` sends it to its home page (the first
item):

| Role             | Menu                      | Pages                       |
| ---------------- | ------------------------- | --------------------------- |
| Student          | Projects, My team         | `/projects`, `/team`        |
| Supervisor       | My projects, Projects     | `/my-projects`, `/projects` |
| Instructor or TA | Teams, Projects           | `/teams`, `/projects`       |
| Everyone         | Demo (bottom of the menu) | `/demo`                     |

URLs name things, not roles: there's one `/projects/:id` page, and it shows
each role its own actions (students apply, the project's supervisor accepts or
declines, course staff see every application). So switching user on a page
shows the same status from the other side, which is what the PoC demo needs
to show, and a link works for whoever opens it.

Pages for a single role (`/team`, `/my-projects`, `/teams`) are wrapped in
`RequireRole` (`src/components/require-role.tsx`). Anyone else sees who the page is for, rather than a 404. This
only shapes the UI; the backend decides what each user may do.

## Scripts

| Command              | What it does                                          |
| -------------------- | ----------------------------------------------------- |
| `npm run dev`        | Regenerate the API types, then start the dev server   |
| `npm run build`      | Type-check and build for production into `dist/`      |
| `npm run preview`    | Serve the production build locally                    |
| `npm test`           | Run the tests once                                    |
| `npm run test:watch` | Re-run tests as you edit                              |
| `npm run coverage`   | Run the tests with a coverage report in `coverage/`   |
| `npm run lint`       | ESLint                                                |
| `npm run format`     | Format everything with Prettier                       |
| `npm run gen:api`    | Regenerate the API types from the backend (see below) |

CI runs `gen:api`, `npm audit`, `format:check`, `lint`, `build` and
`coverage` on every pull request that touches the frontend or the backend's
API code.

## Editor setup

Open the repo root in VS Code and install the recommended extensions it
suggests (Prettier, ESLint, Ruff). Files are formatted on save with the
project's Prettier settings.

## How the code is organised

The layout follows [bulletproof-react](https://github.com/alan2207/bulletproof-react)'s
[project structure](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md),
a widely used reference for structuring React apps:

```
src/
  main.tsx              Entry point: fonts, then <App />
  app/                  The application layer
    index.tsx           App: providers around the router
    provider.tsx        Data cache and theme around the whole app
    router.tsx          Every route and the page it renders
    routes/             One file per page: projects.tsx, my-team.tsx, ...
  components/           Shared components
    layouts/            Side menu, phone navbar, header, user switcher;
                        nav-items.tsx has each role's menu
    require-role.tsx    Limits a page to some roles
  config/
    paths.ts            Every URL, for links
  features/             One folder per area of the product (see its README)
  lib/                  Libraries set up for Keystone
    api-client.ts       The typed API client
    auth.tsx            Who the app is acting as, and their token
    authorization.ts    Roles
    react-query.ts      The data cache
    theme/              Colours, fonts and component styling
  testing/              Test setup, helpers and the fake backend
  types/                Generated API types (not committed)
```

Code flows one way: shared code (`components`, `config`, `lib`, `types`)
→ `features` → `app`. Shared code can't import features or the app, features
can't import the app, and features don't import each other; a page in
`app/routes` puts them together. `npm run lint` checks this, and that files
and folders are named in kebab-case (`user-switcher.tsx`).

Some conventions:

- **Pages stay thin.** A page in `app/routes` lays out components from
  features. The components, requests and hooks themselves go in the feature
  (`features/projects/api/get-projects.ts`,
  `features/projects/components/project-card.tsx`). Move something to
  `components/` only once a second feature needs it.
- **Import with `@/`**, which is `src/`: `import { api } from '@/lib/api-client'`.
  Import files directly, not through an `index.ts` that re-exports a folder.
- **Link with `paths`**, not strings: `<Link to={paths.projectDetail(id)}>`.
- **Use MUI components** rather than hand-built ones, and style with the `sx`
  prop. The theme already styles them; see [`src/lib/theme`](src/lib/theme/README.md).
- **Controls must be at least 40 px** (SRS LF-A1). MUI's `size="medium"`
  buttons and icon buttons are 40 px in this theme; `small` ones are 36 px.

## Adding a page

1. Create the page in `src/app/routes`, for example `project-edit.tsx`,
   exporting a named component. Put its components and requests in the
   feature it belongs to.
2. Add its URL to `src/config/paths.ts`.
3. Add a route for it in `src/app/router.tsx`, inside the `AppLayout`
   children. If only some roles use it, wrap it in `RequireRole`.
4. If it belongs in a menu, add it to those roles' lists in
   `src/components/layouts/nav-items.tsx`.
5. Add a test (see below). To render as a user, call `await actAs(alice)`
   (from `@/lib/auth`, with users from `@/testing/mocks/fixtures`) before
   `renderApp`.

## Talking to the backend

`@/lib/api-client` exports `api`, a client typed from the backend's OpenAPI
schema. Paths, parameters and response bodies are all checked by TypeScript:

```ts
const { data, error } = await api.GET('/api/projects/{project_id}', {
  params: { path: { project_id: projectId } },
})
```

The types (`src/types/api.d.ts`) are generated, not committed.
`npm run dev` regenerates them every time it starts, and CI does too, so they
can't go stale. After changing a backend endpoint while the dev server is
running, run `npm run gen:api`.

Read data with TanStack Query's `useQuery` and change it with `useMutation`,
so pages share a cache and refetch after changes. Following bulletproof-react,
each request gets a file in its feature's `api/` folder with the request and
its hook:

```ts
// src/features/projects/api/get-projects.ts
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/projects')
      if (error) throw new Error('Could not load projects.', { cause: error })
      return data
    },
  })
}
```

After a mutation, invalidate the keys it affects
(`queryClient.invalidateQueries({ queryKey: ['projects'] })`).

To know who the app is acting as, use `useActingAs()` from `@/lib/auth`. It
returns the user, or `null` if nobody is picked.

## Tests

Tests use Vitest and React Testing Library. They go in a `__tests__` folder
beside the code they test (`components/layouts/__tests__/user-switcher.test.tsx`).

- `renderApp('/some/url')` from `@/testing/test-utils` renders the whole app
  at a URL, with fresh providers. Use it for page tests.
- API calls go to a fake backend built with MSW
  (`src/testing/mocks/server.ts`), with sample users in
  `src/testing/mocks/fixtures.ts`. A request with no fake answer fails the
  test. To answer one differently in a single test:

  ```ts
  server.use(http.get('/api/projects', () => HttpResponse.json([someProject])))
  ```

- Find elements the way a user would: by role and accessible name
  (`screen.getByRole('button', { name: 'Apply' })`), not by class or test id.

## Design

The look comes from MUI's free dashboard template. See
[`src/lib/theme/README.md`](src/lib/theme/README.md) for where it came from and what
was changed. Keystone uses only free MUI packages (no MUI X Pro or Premium).
