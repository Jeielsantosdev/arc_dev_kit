'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import type { Locale } from '@/lib/i18n'

interface LanguageContextValue {
  lang: Locale
  setLang: (l: Locale) => void
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: 'pt',
  setLang: () => {},
})

export function LanguageProvider({
  children,
  initialLang,
}: {
  children: ReactNode
  initialLang: Locale
}) {
  const [lang, setLangState] = useState<Locale>(initialLang)
  const router = useRouter()

  const setLang = useCallback(
    (l: Locale) => {
      document.cookie = `arc-lang=${l}; path=/; max-age=${60 * 60 * 24 * 365}`
      setLangState(l)
      router.refresh()
    },
    [router]
  )

  return (
    <LanguageContext.Provider value={{ lang, setLang }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
