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
    colors: ['#EDF1E7', '#FDFEFB', '#47684E', '#DDE3D6'],
  },
  {
    id: 'cobalt',
    name: 'Cobalt Graphite',
    subtitle: '深海军蓝 + 纸白 + 钴蓝',
    colors: ['#17243B', '#F4F6FA', '#315BCE', '#DCE3ED'],
  },
  {
    id: 'guofeng',
    name: '国风',
    subtitle: '宣纸 + 朱砂 + 墨色',
    colors: ['#EEE5D4', '#FFFCF5', '#9C3C2E', '#DDD0BB'],
  },
  {
    id: 'claude',
    name: 'Claude 暖纸',
    subtitle: '米白纸 + 陶土橙 + 暖棕',
    colors: ['#EAE4D9', '#FFFCF7', '#AA5033', '#E0D7CA'],
  },
  {
    id: 'sky',
    name: '天空蓝',
    subtitle: '冷白 + 天蓝 + 深海蓝',
    colors: ['#E7F2F9', '#FFFFFF', '#076B9D', '#D6E6F1'],
  },
  {
    id: 'ghibli',
    name: '宫崎骏风',
    subtitle: '森系手绘 + 森林绿 + 夕照橙',
    colors: ['#293E30', '#FFFDF5', '#507240', '#DCDCC8'],
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
