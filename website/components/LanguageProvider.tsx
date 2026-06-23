'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { setLanguage } from '@/lib/actions'
import type { Locale } from '@/lib/i18n'

interface LanguageContextValue {
  lang: Locale
  setLang: (l: Locale) => Promise<void>
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: 'pt',
  setLang: async () => {},
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
    async (l: Locale) => {
      setLangState(l)
      await setLanguage(l)
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
