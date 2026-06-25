import type { Locale } from './i18n'

export interface NavItem {
  title: string
  slug: string[]
}

export interface NavGroup {
  section: string
  items: NavItem[]
}

export const NAV_PT: NavGroup[] = [
  {
    section: 'Início',
    items: [
      { title: 'Introdução', slug: ['introduction'] },
      { title: 'Instalação', slug: ['getting-started'] },
      { title: 'Configuração', slug: ['configuration'] },
    ],
  },
  {
    section: 'Módulos',
    items: [
      { title: 'Dev Copilot', slug: ['modules', 'dev-copilot'] },
      { title: 'Payment Agent', slug: ['modules', 'payment-agent'] },
      { title: 'Monitor Agent', slug: ['modules', 'monitor-agent'] },
      { title: 'Async Monitor', slug: ['modules', 'async-monitor'] },
      { title: 'Tx Debugger', slug: ['modules', 'tx-debugger'] },
      { title: 'Portfolio Analyzer', slug: ['modules', 'portfolio-analyzer'] },
      { title: 'USDC Token', slug: ['modules', 'usdc-token'] },
      { title: 'Contracts', slug: ['modules', 'contracts'] },
      { title: 'Event Listener', slug: ['modules', 'event-listener'] },
      { title: 'Contract Deployer', slug: ['modules', 'contract-deployer'] },
    ],
  },
  {
    section: 'Interfaces',
    items: [
      { title: 'CLI Reference', slug: ['cli-reference'] },
      { title: 'REST API', slug: ['rest-api'] },
      { title: 'WebSocket', slug: ['websocket'] },
    ],
  },
  {
    section: 'Guias',
    items: [
      { title: 'Cookbook', slug: ['cookbook'] },
      { title: 'Exemplos Práticos', slug: ['examples'] },
      { title: 'Contribuindo', slug: ['contributing'] },
    ],
  },
]

export const NAV_EN: NavGroup[] = [
  {
    section: 'Start',
    items: [
      { title: 'Introduction', slug: ['introduction'] },
      { title: 'Installation', slug: ['getting-started'] },
      { title: 'Configuration', slug: ['configuration'] },
    ],
  },
  {
    section: 'Modules',
    items: [
      { title: 'Dev Copilot', slug: ['modules', 'dev-copilot'] },
      { title: 'Payment Agent', slug: ['modules', 'payment-agent'] },
      { title: 'Monitor Agent', slug: ['modules', 'monitor-agent'] },
      { title: 'Async Monitor', slug: ['modules', 'async-monitor'] },
      { title: 'Tx Debugger', slug: ['modules', 'tx-debugger'] },
      { title: 'Portfolio Analyzer', slug: ['modules', 'portfolio-analyzer'] },
      { title: 'USDC Token', slug: ['modules', 'usdc-token'] },
      { title: 'Contracts', slug: ['modules', 'contracts'] },
      { title: 'Event Listener', slug: ['modules', 'event-listener'] },
      { title: 'Contract Deployer', slug: ['modules', 'contract-deployer'] },
    ],
  },
  {
    section: 'Interfaces',
    items: [
      { title: 'CLI Reference', slug: ['cli-reference'] },
      { title: 'REST API', slug: ['rest-api'] },
      { title: 'WebSocket', slug: ['websocket'] },
    ],
  },
  {
    section: 'Guides',
    items: [
      { title: 'Cookbook', slug: ['cookbook'] },
      { title: 'Practical Examples', slug: ['examples'] },
      { title: 'Contributing', slug: ['contributing'] },
    ],
  },
]

export function getNav(locale: Locale): NavGroup[] {
  return locale === 'en' ? NAV_EN : NAV_PT
}

export const NAV = NAV_PT
