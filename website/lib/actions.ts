'use server'
import { cookies } from 'next/headers'

export async function setLanguage(locale: 'pt' | 'en') {
  const store = await cookies()
  store.set('arc-lang', locale, { path: '/', maxAge: 60 * 60 * 24 * 365 })
}
