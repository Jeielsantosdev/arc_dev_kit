'use client'

import { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { Footer } from './Footer'
import { cn } from '@/lib/utils'

export function DocsLayout({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-zinc-950">
      <Header
        onMenuToggle={() => setMenuOpen((v) => !v)}
        menuOpen={menuOpen}
      />
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      <main
        className={cn(
          'pt-14 min-h-screen',
          'lg:pl-[280px]'
        )}
      >
        <div className="max-w-4xl mx-auto px-6 py-10">
          {children}
        </div>
        <Footer />
      </main>
    </div>
  )
}
