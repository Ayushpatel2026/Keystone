import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import prettier from 'eslint-config-prettier/flat'
import pluginQuery from '@tanstack/eslint-plugin-query'
import importX from 'eslint-plugin-import-x'
import { createTypeScriptImportResolver } from 'eslint-import-resolver-typescript'
import checkFile from 'eslint-plugin-check-file'

export default defineConfig([
  globalIgnores(['dist', 'coverage', 'src/types/api.d.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      pluginQuery.configs['flat/recommended'],
    ],
    languageOptions: {
      globals: globals.browser,
      // Typed rules (recommendedTypeChecked) need the TS project to get type info.
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },

  // Folder rules from bulletproof-react's project structure
  // (https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md).
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { 'import-x': importX, 'check-file': checkFile },
    settings: {
      // Lets the rules follow "@/..." imports to real files.
      'import-x/resolver-next': [createTypeScriptImportResolver()],
    },
    rules: {
      // Code flows one way: shared code -> features -> app. Shared code can't
      // import features or the app, and features can't import the app.
      // A feature also shouldn't import another feature: compose them in
      // src/app instead. Add a zone for each new feature, like the example.
      'import-x/no-restricted-paths': [
        'error',
        {
          zones: [
            { target: './src/features', from: './src/app' },
            {
              target: [
                './src/components',
                './src/config',
                './src/hooks',
                './src/lib',
                './src/types',
                './src/utils',
              ],
              from: ['./src/features', './src/app'],
            },
            {
              target: './src/features/projects',
              from: './src/features',
              except: ['./projects'],
            },
            {
              target: './src/features/courses',
              from: './src/features',
              except: ['./courses'],
            },
            {
              target: './src/features/applications',
              from: './src/features',
              except: ['./applications'],
            },
            {
              target: './src/features/teams',
              from: './src/features',
              except: ['./teams'],
            },
          ],
        },
      ],
      // Import across folders with "@/...", not "../../...".
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['../*'],
              message: 'Use an "@/..." import for files in other folders.',
            },
          ],
        },
      ],
      // File and folder names in kebab-case: user-switcher.tsx, my-team.tsx.
      'check-file/filename-naming-convention': [
        'error',
        { 'src/**/*.{ts,tsx}': 'KEBAB_CASE' },
        { ignoreMiddleExtensions: true },
      ],
      'check-file/folder-naming-convention': [
        'error',
        { 'src/**/!(__tests__)': 'KEBAB_CASE' },
      ],
    },
  },
  {
    // Copied from MUI's dashboard template; keeps its own file names so it's
    // easy to compare with the original.
    files: ['src/lib/theme/**'],
    rules: {
      'check-file/filename-naming-convention': 'off',
      'no-restricted-imports': 'off',
    },
  },

  // Last, so it switches off any style rules that would fight Prettier.
  prettier,
])
