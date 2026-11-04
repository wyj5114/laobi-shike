<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, ChevronRight, FileDown, Folder, Search } from 'lucide-vue-next'
import { useLibraryStore } from '@/stores/library'
import { api } from '@/services/api'
import PaginationBar from '@/components/common/PaginationBar.vue'

const router = useRouter()
const library = useLibraryStore()
const query = ref('')
const page = ref(1)
const pageSize = 50

onMounted(() => library.load())

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return library.sortedNotes
  return library.sortedNotes.filter(n => n.title.toLowerCase().includes(q) || n.author.toLowerCase().includes(q))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const pagedNotes = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const pageGroups = computed(() =>
  library.sortedGroups
    .map(group => ({ ...group, notes: pagedNotes.value.filter(note => note.groupId === group.id) }))
    .filter(group => group.notes.length),
)
const pageUngrouped = computed(() => pagedNotes.value.filter(note => note.groupId === null))

watch(query, () => { page.value = 1 })
watch(totalPages, total => { if (page.value > total) page.value = total })

function notesOf(groupId: string | null) {
  return filtered.value.filter(n => n.groupId === groupId)
}

async function downloadGroup(groupId: string | null, name: string) {
  try {
    const blob = await api.exportGroup(groupId ?? 'ungrouped')
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${name.replace(/[\\/:*?"<>|]/g, '_')}-笔记.zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    window.alert(error instanceof Error ? error.message : String(error))
  }
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="page-frame library-page">
      <div class="page-heading flex items-end justify-between">
        <div>
          <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Library</p>
          <h1 class="mt-2 text-[30px] font-semibold tracking-[-0.025em]">笔记库</h1>
        </div>
        <div class="glass-chip flex h-9 w-[240px] items-center gap-2 rounded-[9px] px-3 text-[12.5px] text-faint">
          <Search :size="14" />
          <input v-model="query" class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-faint" placeholder="搜索标题或 UP 主" />
        </div>
      </div>

      <div v-for="group in pageGroups" :key="group.id" class="library-group mt-7">
        <button class="flex w-full items-center gap-2 border-b border-line py-3 text-left" @click="library.toggleGroup(group.id)">
          <Folder :size="15" class="text-accent" />
          <span class="text-[13.5px] font-medium">{{ group.name }}</span>
          <span class="text-[11.5px] text-faint">{{ notesOf(group.id).length }} 篇</span>
          <component :is="library.collapsed[group.id] ? ChevronRight : ChevronDown" :size="15" class="ml-auto text-faint" />
          <button class="flex h-6 w-6 items-center justify-center rounded border border-line text-faint hover:border-accent hover:text-accent" title="下载本组全部 Markdown" @click.stop="downloadGroup(group.id, group.name)">
            <FileDown :size="12" />
          </button>
        </button>

        <ul v-if="!library.collapsed[group.id]">
          <li
            v-for="note in group.notes"
            :key="note.id"
            class="note-list-row flex cursor-pointer items-center gap-5 border-b border-line-soft py-4 hover:bg-surface-2"
            @click="router.push(note.status === 'done' ? `/notes/${note.id}` : `/tasks/${note.id}`)"
          >
            <span class="w-[86px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
            <div class="min-w-0">
              <p class="truncate text-[15px] font-medium">{{ note.title }}</p>
              <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
            </div>
            <span
              class="status-pill ml-auto text-[11.5px]"
              :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
            >
              {{ note.status === 'done' ? '已完成' : note.status === 'running' ? '进行中' : note.status === 'pending' ? '未开始' : '失败' }}
            </span>
          </li>
        </ul>
      </div>

      <div v-if="pageUngrouped.length" class="library-group mt-7">
        <button class="flex w-full items-center gap-2 border-b border-line py-3 text-left" @click="library.toggleGroup('ungrouped')">
          <Folder :size="15" class="text-muted" />
          <span class="text-[13.5px] font-medium">未分组</span>
          <span class="text-[11.5px] text-faint">{{ notesOf(null).length }} 篇</span>
          <component :is="library.collapsed.ungrouped ? ChevronRight : ChevronDown" :size="15" class="ml-auto text-faint" />
        </button>
        <ul v-if="!library.collapsed.ungrouped">
          <li
            v-for="note in pageUngrouped"
            :key="note.id"
            class="note-list-row flex cursor-pointer items-center gap-5 border-b border-line-soft py-4 hover:bg-surface-2"
            @click="router.push(note.status === 'done' ? `/notes/${note.id}` : `/tasks/${note.id}`)"
          >
            <span class="w-[86px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
            <div class="min-w-0">
              <p class="truncate text-[15px] font-medium">{{ note.title }}</p>
              <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
            </div>
            <span
              class="status-pill ml-auto text-[11.5px]"
              :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
            >
              {{ note.status === 'done' ? '已完成' : note.status === 'running' ? '进行中' : note.status === 'pending' ? '未开始' : '失败' }}
            </span>
          </li>
        </ul>
      </div>

      <PaginationBar v-model:page="page" :total-pages="totalPages" :total="filtered.length" :page-size="pageSize" />
    </div>
  </div>
</template>
