// Tokens every theme must define (issue #21) — the full set app.css and
// component styles actually read. Kept here (not derived from app.css) so
// importTheme can validate an imported theme up front, rather than letting
// it apply half-defined and leave stale values from whatever theme was
// active before it.
export const REQUIRED_TOKENS = [
  '--bg',
  '--surface',
  '--surface-alt',
  '--border',
  '--text',
  '--text-muted',
  '--accent',
  '--accent-text',
  '--accent-soft-bg',
  '--accent-soft-border',
  '--shadow-color',
  '--error-bg',
  '--error-text',
  '--font-family',
  '--radius-sm',
  '--radius-md',
  '--radius-lg',
  '--radius-pill',
  '--color-scheme',
]

// Built-in themes ship as app code, not user data — unlike imported themes
// (backend's custom_themes, see api.js), these don't need a round trip to
// the backend just to list them.
export const builtInThemes = [
  {
    id: 'default-dark',
    name: 'Default - Dark',
    tokens: {
      '--bg': '#1c1712',
      '--surface': '#241d16',
      '--surface-alt': '#2a2018',
      '--border': '#3d3020',
      '--text': '#f2e6d8',
      '--text-muted': '#b8a488',
      '--accent': '#e8952f',
      '--accent-text': '#1c1712',
      '--accent-soft-bg': '#3d2a12',
      '--accent-soft-border': '#6b4a1e',
      '--shadow-color': 'rgba(0, 0, 0, 0.35)',
      '--error-bg': '#3d211f',
      '--error-text': '#f0958a',
      '--font-family': '-apple-system, system-ui, sans-serif',
      '--radius-sm': '0.5rem',
      '--radius-md': '0.75rem',
      '--radius-lg': '1rem',
      '--radius-pill': '999px',
      '--color-scheme': 'dark',
    },
  },
  {
    id: 'default-light',
    name: 'Default - Light',
    tokens: {
      '--bg': '#faf6f1',
      '--surface': '#ffffff',
      '--surface-alt': '#f5ede4',
      '--border': '#e0d3c2',
      '--text': '#2a2015',
      '--text-muted': '#8a7259',
      '--accent': '#c2650a',
      '--accent-text': '#fff8f0',
      '--accent-soft-bg': '#ffe9d5',
      '--accent-soft-border': '#f0b876',
      '--shadow-color': 'rgba(40, 25, 10, 0.1)',
      '--error-bg': '#fbe3e0',
      '--error-text': '#a3392c',
      '--font-family': '-apple-system, system-ui, sans-serif',
      '--radius-sm': '0.5rem',
      '--radius-md': '0.75rem',
      '--radius-lg': '1rem',
      '--radius-pill': '999px',
      '--color-scheme': 'light',
    },
  },
  {
    // Recreates issue #20's cool palette (dark variant) — the values below
    // are the same ones that used to live under app.css's
    // [data-palette='cool'] light-dark(light, dark) pairs, before issue #21
    // replaced the toggle with named themes.
    id: 'cool-dark',
    name: 'Cool - Dark',
    tokens: {
      '--bg': '#10171c',
      '--surface': '#17212a',
      '--surface-alt': '#1c2830',
      '--border': '#2b3c47',
      '--text': '#e4edf2',
      '--text-muted': '#93a8b3',
      '--accent': '#4fa3e0',
      '--accent-text': '#0b1116',
      '--accent-soft-bg': '#16283a',
      '--accent-soft-border': '#235279',
      '--shadow-color': 'rgba(0, 0, 0, 0.35)',
      '--error-bg': '#3d211f',
      '--error-text': '#f0958a',
      '--font-family': '-apple-system, system-ui, sans-serif',
      '--radius-sm': '0.5rem',
      '--radius-md': '0.75rem',
      '--radius-lg': '1rem',
      '--radius-pill': '999px',
      '--color-scheme': 'dark',
    },
  },
  {
    // Recreates issue #20's cool palette (light variant) — see cool-dark.
    id: 'cool-light',
    name: 'Cool - Light',
    tokens: {
      '--bg': '#f1f6f8',
      '--surface': '#ffffff',
      '--surface-alt': '#e8eef2',
      '--border': '#ccdae3',
      '--text': '#16232b',
      '--text-muted': '#5f7684',
      '--accent': '#1f6fb2',
      '--accent-text': '#f5fbff',
      '--accent-soft-bg': '#dcedfa',
      '--accent-soft-border': '#8ec3e8',
      '--shadow-color': 'rgba(10, 30, 45, 0.1)',
      '--error-bg': '#fbe3e0',
      '--error-text': '#a3392c',
      '--font-family': '-apple-system, system-ui, sans-serif',
      '--radius-sm': '0.5rem',
      '--radius-md': '0.75rem',
      '--radius-lg': '1rem',
      '--radius-pill': '999px',
      '--color-scheme': 'light',
    },
  },
]

export const DEFAULT_THEME_ID = 'default-dark'

// Applied to <html> rather than scoped to a component, same reasoning as
// the old data-palette attribute it replaces: tokens need to cascade to the
// whole page, including dialogs mounted outside <main>.
export function applyTheme(theme) {
  const root = document.documentElement.style
  for (const token of REQUIRED_TOKENS) {
    root.setProperty(token, theme.tokens[token] ?? '')
  }
}

// Used by the import dialog to reject a theme missing tokens the app
// actually reads, rather than letting it apply with silent gaps.
export function missingTokens(tokens) {
  return REQUIRED_TOKENS.filter((token) => !tokens || typeof tokens[token] !== 'string' || tokens[token] === '')
}
