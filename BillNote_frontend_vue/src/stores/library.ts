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
    // 从后端加载实际学习记录，空库展示首次学习引导。
    groups: [],
    notes: [],
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
        this.groups = groups.map(g => ({ id: g.id, name: g.name, order: g.order }))
        this.notes = items.map(toSummary)
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
