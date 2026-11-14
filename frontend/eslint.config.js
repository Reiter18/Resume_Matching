import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  { ignores: ['dist', 'node_modules'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'module', globals: { ...globals.browser, ...globals.node, ...globals.vitest }, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { react, 'react-hooks': reactHooks },
    settings: { react: { version: 'detect' } },
    rules: { 'react/jsx-uses-vars': 'error', 'react/jsx-uses-react': 'off', ...reactHooks.configs.recommended.rules },
  },
]
