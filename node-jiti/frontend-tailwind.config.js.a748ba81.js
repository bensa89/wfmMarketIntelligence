"use strict";Object.defineProperty(exports, "__esModule", {value: true});/** @type {import('tailwindcss').Config} */
exports. default = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      colors: {
        sidebar: {
          bg:           '#0f172a',
          text:         'rgba(248,250,252,0.45)',
          'text-active':'#93c5fd',
          'active-bg':  'rgba(37,99,235,0.18)',
          border:       'rgba(255,255,255,0.06)',
          label:        'rgba(248,250,252,0.20)',
        },
        app: {
          bg:           '#f8f8fa',
          card:         '#ffffff',
          border:       '#ececf0',
          'border-sub': '#f4f4f6',
        },
        ink: {
          DEFAULT: '#09090b',
          secondary: '#71717a',
          muted:    '#a1a1aa',
        },
        accent: {
          blue:   '#2563eb',
          purple: '#7c3aed',
        },
        signal: {
          high:   '#10b981',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
 /* v7-cff9fdce28ac6445 */