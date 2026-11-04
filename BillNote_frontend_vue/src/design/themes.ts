export type ThemeId = 'study' | 'cobalt' | 'guofeng' | 'claude' | 'sky' | 'ghibli'

export interface ThemeOption {
  id: ThemeId
  name: string
  subtitle: string
  colors: [string, string, string, string]
}

export const THEMES: ThemeOption[] = [
  {
    id: 'study',
    name: '青笺 · 学习空间',
    subtitle: '暖白纸张 + 鼠尾草绿 + 墨色',
    colors: ['#F3F4EE', '#FAFAF6', '#486B55', '#E1E5DC'],
  },
  {
    id: 'cobalt',
    name: 'Cobalt Graphite',
    subtitle: '深海军蓝 + 纸白 + 钴蓝',
    colors: ['#0B1220', '#F6F7F9', '#2563EB', '#E2E8F0'],
  },
  {
    id: 'guofeng',
    name: '国风',
    subtitle: '宣纸 + 朱砂 + 墨色',
    colors: ['#241C16', '#F3EEE2', '#A23B2A', '#D8CBB8'],
  },
  {
    id: 'claude',
    name: 'Claude 暖纸',
    subtitle: '米白纸 + 陶土橙 + 暖棕',
    colors: ['#3A342C', '#EFECE4', '#C15F3C', '#D8D2C5'],
  },
  {
    id: 'sky',
    name: '天空蓝',
    subtitle: '冷白 + 天蓝 + 深海蓝',
    colors: ['#0B3A5A', '#EDF6FF', '#0284C7', '#CFE4F3'],
  },
  {
    id: 'ghibli',
    name: '宫崎骏风',
    subtitle: '森系手绘 + 森林绿 + 夕照橙',
    colors: ['#2A3328', '#F4F0E4', '#4F7A4A', '#D98E4A'],
  },
]

const STORAGE_KEY = 'shike-theme'

export function isThemeId(value: string | null): value is ThemeId {
  return THEMES.some(theme => theme.id === value)
}

export function getStoredTheme(): ThemeId {
  const preview = new URLSearchParams(window.location.search).get('theme')
  if (isThemeId(preview)) return preview
  const stored = localStorage.getItem(STORAGE_KEY)
  return isThemeId(stored) ? stored : 'study'
}

export function applyTheme(id: ThemeId) {
  document.documentElement.dataset.theme = id
  localStorage.setItem(STORAGE_KEY, id)
  // 预览用 ?theme= 只生效一次，避免后续刷新覆盖用户选择
  const url = new URL(window.location.href)
  if (url.searchParams.has('theme')) {
    url.searchParams.delete('theme')
    window.history.replaceState(null, '', url.toString())
  }
}
