import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#FDF6F0',
        accent: { DEFAULT: '#E8734A', hover: '#D4623B', soft: '#FDE8DF' },
        ink: { DEFAULT: '#1A1A1A', soft: '#6B7280' },
        line: 'rgba(0,0,0,0.06)',
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', 'Inter', 'sans-serif'],
      },
      borderRadius: { card: '16px', input: '10px', btn: '8px' },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)',
        pop: '0 8px 30px rgba(0,0,0,0.12)',
      },
    },
  },
  plugins: [],
} satisfies Config;
