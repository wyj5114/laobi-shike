import { defineStore } from 'pinia'
import { api, type ApiNote } from '@/services/api'
import { cleanNoteTitle } from '@/utils/note'

export interface NoteSummary {
  id: string
  title: string
  author: string
  duration: string
  style: string
  status: 'done' | 'running' | 'pending' | 'failed'
  createdAt: string
  groupId: string | null
}

export interface NoteGroup {
  id: string
  name: string
  order: number
}

interface LibraryState {
  groups: NoteGroup[]
  notes: NoteSummary[]
  collapsed: Record<string, boolean>
  loaded: boolean
  loading: boolean
  error: string | null
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}

function formatDate(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function toSummary(note: ApiNote): NoteSummary {
  const raw = note.status || 'PENDING'
  const status =
    raw === 'SUCCESS' ? 'done' : raw === 'FAILED' ? 'failed' : raw === 'PENDING' ? 'pending' : 'running'
  return {
    id: note.id,
    title: cleanNoteTitle(note.title),
    author: note.platform === 'bilibili' ? 'B 站' : note.platform,
    duration: formatDuration(note.duration),
    style: 'B 站笔记',
    status,
    createdAt: formatDate(note.created_at),
    groupId: note.group_id,
  }
}

/** 已完成 → 进行中 → 未开始 → 失败；同状态按标题数字自然升序。 */
export function sortNotes(notes: NoteSummary[]): NoteSummary[] {
  const rank: Record<NoteSummary['status'], number> = { done: 0, running: 1, pending: 2, failed: 3 }
  return [...notes].sort((a, b) => {
    const byStatus = rank[a.status] - rank[b.status]
    if (byStatus !== 0) return byStatus
    return a.title.localeCompare(b.title, 'zh-CN', { numeric: true, sensitivity: 'base' })
  })
}

export const useLibraryStore = defineStore('library', {
  state: (): LibraryState => ({
    // 首次打开且后端无数据时保留演示内容；一旦后端有数据就以 API 为准。
    groups: [
      { id: 'kaoyan', name: '考研数学', order: 0 },
      { id: 'network', name: '计算机网络', order: 1 },
    ],
    notes: [
      {
        id: 'demo',
        title: '线性代数第 12 讲：特征值与特征向量',
        author: '3BlueBrown',
        duration: '42:18',
        style: '详细风格',
        status: 'done',
        createdAt: '今天 14:20',
        groupId: 'kaoyan',
      },
      {
        id: 'prob-6',
        title: '概率论第 6 讲：条件概率与贝叶斯公式',
        author: '数学系的小林',
        duration: '38:02',
        style: '学术风格',
        status: 'done',
        createdAt: '今天 10:05',
        groupId: 'kaoyan',
      },
      {
        id: 'tcp',
        title: '计算机网络：TCP 三次握手到底在做什么',
        author: 'CS 自学指南',
        duration: '26:40',
        style: '教程风格',
        status: 'running',
        createdAt: '昨天',
        groupId: 'network',
      },
      {
        id: 'english-3',
        title: '考研英语长难句拆解 · 第 3 期',
        author: '英语老师阿哲',
        duration: '51:12',
        style: '精简风格',
        status: 'done',
        createdAt: '10 月 30 日',
        groupId: null,
      },
    ],
    collapsed: {},
    loaded: false,
    loading: false,
    error: null,
  }),

  getters: {
    sortedGroups: state => [...state.groups].sort((a, b) => a.order - b.order),
    sortedNotes: state => sortNotes(state.notes),
    ungrouped: state => sortNotes(state.notes.filter(n => n.groupId === null)),
    notesOfGroup: state => (groupId: string) => sortNotes(state.notes.filter(n => n.groupId === groupId)),
    groupName: state => (groupId: string | null) =>
      state.groups.find(g => g.id === groupId)?.name ?? '未分组',
  },

  actions: {
    async load() {
      if (this.loading) return
      this.loading = true
      this.error = null
      try {
        const [groups, firstPage] = await Promise.all([
          api.listGroups(),
          api.listNotes({ page: 1, page_size: 200 }),
        ])
        const items: ApiNote[] = [...firstPage.items]
        let page = 2
        while (items.length < firstPage.total && page <= 20) {
          const next = await api.listNotes({ page, page_size: 200 })
          if (!next.items.length) break
          items.push(...next.items)
          page += 1
        }
        if (groups.length || items.length) {
          this.groups = groups.map(g => ({ id: g.id, name: g.name, order: g.order }))
          this.notes = items.map(toSummary)
        }
        this.loaded = true
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },

    async createGroup(name: string) {
      const trimmed = name.trim()
      if (!trimmed) return null
      try {
        const group = await api.createGroup(trimmed)
        this.groups.push({ id: group.id, name: group.name, order: group.order })
        return group
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        return null
      }
    },

    async renameGroup(id: string, name: string) {
      const trimmed = name.trim()
      if (!trimmed) return false
      try {
        const updated = await api.updateGroup(id, { name: trimmed })
        const group = this.groups.find(g => g.id === id)
        if (group) group.name = updated.name
        return true
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        return false
      }
    },

    async deleteGroup(id: string) {
      try {
        await api.deleteGroup(id)
        this.groups = this.groups.filter(g => g.id !== id)
        this.notes.forEach(note => {
          if (note.groupId === id) note.groupId = null
        })
        return true
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        return false
      }
    },

    toggleGroup(id: string) {
      this.collapsed[id] = !this.collapsed[id]
    },

    async moveNote(noteId: string, groupId: string | null) {
      const note = this.notes.find(n => n.id === noteId)
      if (!note) return
      const previous = note.groupId
      note.groupId = groupId
      try {
        await api.moveNote(noteId, groupId)
      } catch (error) {
        note.groupId = previous
        this.error = error instanceof Error ? error.message : String(error)
      }
    },

    addPendingNote(note: Omit<NoteSummary, 'status' | 'createdAt'>) {
      this.notes.unshift({
        ...note,
        status: 'pending',
        createdAt: '刚刚',
      })
    },
  },
})
