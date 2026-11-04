<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, ChevronRight, Folder, LoaderCircle } from 'lucide-vue-next'
import { useLibraryStore, type NoteSummary } from '@/stores/library'
import PaginationBar from '@/components/common/PaginationBar.vue'

const router = useRouter()
const library = useLibraryStore()
const page = ref(1)
const pageSize = 50
const collapsed = ref<Record<string, boolean>>({})

onMounted(() => library.load())

const taskRank: Record<NoteSummary['status'], number> = { running: 0, pending: 1, done: 2, failed: 3 }
const sortedTasks = computed(() =>
  [...library.sortedNotes].sort((a, b) => {
    const byStatus = taskRank[a.status] - taskRank[b.status]
    if (byStatus !== 0) return byStatus
    return a.title.localeCompare(b.title, 'zh-CN', { numeric: true, sensitivity: 'base' })
  }),
)
const totalPages = computed(() => Math.max(1, Math.ceil(sortedTasks.value.length / pageSize)))
const pagedTasks = computed(() => sortedTasks.value.slice((page.value - 1) * pageSize, page.value * pageSize))

const groups = computed(() => {
  const result = library.sortedGroups
    .map(group => ({
      key: group.id,
      name: group.name,
      notes: pagedTasks.value.filter(note => note.groupId === group.id),
    }))
    .filter(group => group.notes.length)
  const ungrouped = pagedTasks.value.filter(note => note.groupId === null)
  if (ungrouped.length) result.push({ key: 'ungrouped', name: '未分组', notes: ungrouped })
  return result
})

const allCollapsed = computed(() => groups.value.length > 0 && groups.value.every(group => collapsed.value[group.key]))

watch(totalPages, total => { if (page.value > total) page.value = total })
watch(() => library.sortedNotes.length, () => { page.value = 1 })

function groupTotal(groupId: string | null): number {
  return sortedTasks.value.filter(note => note.groupId === groupId).length
}

function groupActive(groupId: string | null): number {
  return sortedTasks.value.filter(note => note.groupId === groupId && (note.status === 'running' || note.status === 'pending')).length
}

function toggleGroup(key: string) {
  collapsed.value[key] = !collapsed.value[key]
}

function toggleAll() {
  const target = !allCollapsed.value
  for (const group of groups.value) collapsed.value[group.key] = target
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="page-frame task-list-page">
      <div class="page-heading flex items-end justify-between">
        <div>
          <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Tasks</p>
          <h1 class="mt-2 text-[30px] font-semibold tracking-[-0.025em]">任务</h1>
        </div>
        <button class="h-8 rounded-[8px] border border-line px-3 text-[12px] text-muted hover:bg-surface-2" @click="toggleAll">
          {{ allCollapsed ? '全部展开' : '全部收起' }}
        </button>
      </div>

      <div class="glass-card mt-7 overflow-hidden rounded-[14px]">
        <div v-for="group in groups" :key="group.key">
          <button class="flex w-full items-center gap-2 border-b border-line bg-surface-2/40 px-5 py-3 text-left" @click="toggleGroup(group.key)">
            <Folder :size="15" class="text-accent" />
            <span class="text-[13px] font-medium">{{ group.name }}</span>
            <span class="text-[11px] text-faint">{{ groupTotal(group.key === 'ungrouped' ? null : group.key) }} 项</span>
            <span v-if="groupActive(group.key === 'ungrouped' ? null : group.key)" class="rounded-full bg-accent-soft px-2 py-0.5 text-[10.5px] text-accent">
              {{ groupActive(group.key === 'ungrouped' ? null : group.key) }} 待跑
            </span>
            <component :is="collapsed[group.key] ? ChevronRight : ChevronDown" :size="14" class="ml-auto text-faint" />
          </button>

          <template v-if="!collapsed[group.key]">
            <button
              v-for="note in group.notes"
              :key="note.id"
              class="flex w-full items-center gap-4 border-b border-line-soft px-5 py-4 text-left last:border-0 hover:bg-surface-2"
              @click="router.push(`/tasks/${note.id}`)"
            >
              <LoaderCircle v-if="note.status === 'running'" :size="16" class="animate-spin text-accent" />
              <span v-else class="h-2 w-2 rounded-full" :class="note.status === 'done' ? 'bg-success' : note.status === 'failed' ? 'bg-red-500' : 'bg-faint'" />
              <div class="min-w-0">
                <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
                <p class="mt-1 text-[11.5px] text-faint">{{ note.createdAt }} · {{ note.author }}</p>
              </div>
              <span
                class="status-pill ml-auto text-[11.5px]"
                :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
              >
                {{ note.status === 'done' ? '已完成' : note.status === 'running' ? '进行中' : note.status === 'pending' ? '未开始' : '失败' }}
              </span>
              <ChevronRight :size="15" class="text-faint" />
            </button>
          </template>
        </div>
      </div>

      <PaginationBar v-model:page="page" :total-pages="totalPages" :total="sortedTasks.length" :page-size="pageSize" />
    </div>
  </div>
</template>
