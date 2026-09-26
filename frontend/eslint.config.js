import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';
import { globalIgnores } from 'eslint/config';

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    rules: {
      // Los contextos (AuthContext, UserContext) exportan a propósito el
      // Provider junto con su hook (useAuth, useUser); es el patrón estándar
      // del proyecto. `createDataTableColumnHelper` es un re-export puntual
      // en components/ui/DataTable.tsx.
      'react-refresh/only-export-components': [
        'error',
        { allowExportNames: ['useAuth', 'useUser', 'createDataTableColumnHelper'] },
      ],
    },
  },
]);
