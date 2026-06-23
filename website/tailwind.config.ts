import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './content/**/*.{md,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        arc: {
          50:  '#f0eeff',
          100: '#e3dcff',
          200: '#cabbff',
          300: '#a98aff',
          400: '#8855ff',
          500: '#6d28d9',
          600: '#5b21b6',
          700: '#4c1d95',
          800: '#3b0764',
          900: '#1e0040',
          950: '#0d0020',
        },
        usdc: {
          DEFAULT: '#2775CA',
          light: '#5fa8f0',
          dark: '#1a4d8c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      typography: (theme: (arg: string) => string) => ({
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: theme('colors.zinc.300'),
            a: {
              color: theme('colors.arc.300'),
              '&:hover': { color: theme('colors.arc.200') },
              textDecoration: 'none',
            },
            'h1, h2, h3, h4': {
              color: theme('colors.white'),
              fontWeight: '600',
            },
            code: {
              color: theme('colors.arc.300'),
              backgroundColor: theme('colors.zinc.800'),
              borderRadius: '0.25rem',
              padding: '0.1em 0.35em',
              fontWeight: '400',
            },
            'code::before': { content: '""' },
            'code::after': { content: '""' },
            pre: {
              backgroundColor: theme('colors.zinc.900'),
              border: `1px solid ${theme('colors.zinc.700')}`,
            },
            blockquote: {
              borderLeftColor: theme('colors.arc.500'),
              color: theme('colors.zinc.400'),
            },
            hr: { borderColor: theme('colors.zinc.700') },
            'thead th': { color: theme('colors.white') },
            'tbody tr': { borderBottomColor: theme('colors.zinc.700') },
          },
        },
      }),
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        glow: 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(109, 40, 217, 0.3)' },
          '100%': { boxShadow: '0 0 40px rgba(109, 40, 217, 0.6)' },
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}

export default config
