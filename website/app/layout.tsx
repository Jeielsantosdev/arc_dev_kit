import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'Arc DevKit — Python SDK for the Arc Blockchain',
    template: '%s · Arc DevKit',
  },
  description:
    'Complete Python toolkit for building on Arc (Circle) — Dev Copilot, Payment Agents, Tx Debugger, Portfolio Analyzer, REST API and CLI.',
  keywords: ['arc blockchain', 'circle', 'usdc', 'python sdk', 'web3', 'evm', 'devkit'],
  openGraph: {
    title: 'Arc DevKit',
    description: 'Python SDK for the Arc blockchain by Circle',
    siteName: 'Arc DevKit Docs',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Arc DevKit',
    description: 'Python SDK for the Arc blockchain by Circle',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
