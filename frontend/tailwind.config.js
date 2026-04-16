/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f1117',
          card: '#1a1d2e',
          border: '#2a2d3e',
          text: '#e2e8f0',
          muted: '#94a3b8',
          accent: '#6366f1',
        },
        signal: {
          high: '#22c55e',
          medium: '#eab308',
          low: '#ef4444',
        },
        type: {
          product_update: '#3b82f6',
          ai_announcement: '#8b5cf6',
          partnership: '#06b6d4',
          positioning_change: '#f97316',
          target_market_change: '#ec4899',
          event_or_thought_leadership: '#14b8a6',
          hiring_signal: '#f59e0b',
          other: '#6b7280',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
