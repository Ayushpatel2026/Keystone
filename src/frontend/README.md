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
  running and a `src/backend/.env` file (database settings and
  `KEYSTONE_SECRET_KEY`), run this in `src/backend`:

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

```
src/
  main.tsx              Entry point: fonts, providers, router
  app/                  The app shell
    routes.tsx          Every route and the page it renders
    paths.ts            Every URL, for links
    AppProviders.tsx    Data cache and theme around the whole app
    layout/             Side menu, phone navbar, header, user switcher
  features/             One folder per area of the product
    projects/pages/     Project catalogue and details (#236)
    applications/pages/ A team's applications (#237, #239)
    supervisor/pages/   Supervisor decisions (#238)
    review/pages/       Instructor review (#240)
    demo/pages/         Demo reset (#242)
  components/           Shared pieces used by more than one feature
  api/                  The typed API client and the data cache
  auth/                 Who the app is acting as, and their token
  theme/                Colours, fonts and component styling
  test/                 Test helpers and the fake backend
```

Some conventions:

- **Feature code stays in its feature folder.** A page's own components,
  hooks and API calls go next to it (for example
  `features/projects/components/`, `features/projects/api.ts`). Move
  something to `components/` only once a second feature needs it.
- **Link with `paths`**, not strings: `<Link to={paths.projectDetail(id)}>`.
- **Use MUI components** rather than hand-built ones, and style with the `sx`
  prop. The theme already styles them; see [`src/theme`](src/theme/README.md).
- **Controls must be at least 40 px** (SRS LF-A1). MUI's `size="medium"`
  buttons and icon buttons are 40 px in this theme; `small` ones are 36 px.

## Adding a page

1. Create the page in its feature, for example
   `src/features/projects/pages/ProjectEditPage.tsx`, exporting a named
   component.
2. Add its URL to `src/app/paths.ts`.
3. Add a route for it in `src/app/routes.tsx`, inside the `AppLayout` children.
4. If it belongs in the menu, add it to `src/app/layout/navItems.tsx`.
5. Add a test (see below).

## Talking to the backend

`src/api/client.ts` exports `api`, a client typed from the backend's OpenAPI
schema. Paths, parameters and response bodies are all checked by TypeScript:

```ts
const { data, error } = await api.GET('/api/projects/{project_id}', {
  params: { path: { project_id: projectId } },
})
```

The types (`src/api/schema.d.ts`) are generated, not committed.
`npm run dev` regenerates them every time it starts, and CI does too, so they
can't go stale. After changing a backend endpoint while the dev server is
running, run `npm run gen:api`.

Read data with TanStack Query's `useQuery` and change it with `useMutation`,
so pages share a cache and refetch after changes:

```ts
const projects = useQuery({
  queryKey: ['projects'],
  queryFn: async () => {
    const { data, error } = await api.GET('/api/projects')
    if (error) throw new Error('Could not load projects.', { cause: error })
    return data
  },
})
```

After a mutation, invalidate the keys it affects
(`queryClient.invalidateQueries({ queryKey: ['projects'] })`).

To know who the app is acting as, use `useActingAs()` from
`src/auth/hooks.ts`. It returns the user, or `null` if nobody is picked.

## Tests

Tests use Vitest and React Testing Library, and sit next to the file they test
(`Thing.test.tsx`).

- `renderApp('/some/url')` from `src/test/renderApp.tsx` renders the whole
  app at a URL, with fresh providers. Use it for page tests.
- API calls go to a fake backend built with MSW (`src/test/server.ts`), with
  sample users in `src/test/fixtures.ts`. A request with no fake answer fails
  the test. To answer one differently in a single test:

  ```ts
  server.use(http.get('/api/projects', () => HttpResponse.json([someProject])))
  ```

- Find elements the way a user would: by role and accessible name
  (`screen.getByRole('button', { name: 'Apply' })`), not by class or test id.

## Design

The look comes from MUI's free dashboard template. See
[`src/theme/README.md`](src/theme/README.md) for where it came from and what
was changed. Keystone uses only free MUI packages (no MUI X Pro or Premium).
