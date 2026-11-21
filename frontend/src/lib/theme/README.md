# Theme

Keystone's look comes from MUI's free
[dashboard template](https://mui.com/material-ui/getting-started/templates/dashboard/)
(MIT license, copied from MUI `v9.5.0`). Open that page to see the full
template, including widgets we haven't used yet (stat cards, charts, data grid,
date picker, tree view). Its source code is linked from the same page.

## What's here

- `themePrimitives.ts`: colours, typography (Inter), corner rounding, shadows,
  light and dark modes. Change the overall look here.
- `customizations/`: styling for the core MUI components.
- `customizations/x/`: styling for the MUI X components (charts, data grid,
  date pickers, tree view). It's applied app-wide, so these components are
  styled as soon as someone uses them.
- `AppTheme.tsx`: builds the theme; `src/app/provider.tsx` uses it.
- `ColorModeIconDropdown.tsx`, `ColorModeSelect.tsx`: light/dark switchers.

The template's app frame (side menu, mobile navbar, header, breadcrumbs) was
adapted for Keystone in [`src/components/layouts`](../../components/layouts).

## Changes from the template

- Two type imports from the paid MUI X Pro packages were switched to the free
  packages. Keystone only uses free MUI packages.
- The data grid customizations were converted from JavaScript to TypeScript.
- The font is loaded as `'Inter Variable'` (bundled with the app, see
  `src/main.tsx`) instead of expecting Inter to be installed.
- The colour-mode button got an accessible name, "Change colour theme".
- Formatted with Prettier, with type imports marked `type`, to match the
  project's settings.
