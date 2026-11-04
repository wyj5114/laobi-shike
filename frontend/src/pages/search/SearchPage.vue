<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Folder, Search } from 'lucide-vue-next'
import { useLibraryStore, type NoteSummary } from '@/stores/library'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const query = ref(String(route.query.q || ''))

onMounted(() => library.load())
watch(() => route.query.q, value => { query.value = String(value || '') })

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return library.sortedNotes
  return library.sortedNotes.filter(note =>
    note.title.toLowerCase().includes(q) || note.author.toLowerCase().includes(q),
  )
})

function submit() {
  router.replace({ name: 'search', query: query.value.trim() ? { q: query.value.trim() } : {} })
}

function openNote(note: NoteSummary) {
  router.push(note.status === 'done' ? `/notes/${note.id}` : `/tasks/${note.id}`)
}

function statusText(note: NoteSummary): string {
  return note.status === 'done' ? '已完成' : note.status === 'running' ? '进行中' : note.status === 'pending' ? '未开始' : '失败'
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto w-[860px] pb-24 pt-10">
      <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Search</p>
      <h1 class="mt-2 text-[30px] font-semibold tracking-[-0.025em]">搜索笔记</h1>
      <p class="mt-2 text-[13px] text-muted">输入标题或 UP 主，找到对应笔记。</p>

      <div class="glass-card mt-6 flex h-11 items-center gap-2 rounded-[10px] px-3">
        <Search :size="16" class="text-faint" />
        <input
          v-model="query"
          autofocus
          class="min-w-0 flex-1 bg-transparent text-[13.5px] outline-none placeholder:text-faint"
          placeholder="搜索笔记标题、UP 主…"
          @keydown.enter="submit"
        />
        <kbd class="rounded border border-line bg-surface px-1.5 py-px text-[11px] text-faint">Enter</kbd>
      </div>

      <div class="mt-5 flex items-center justify-between text-[12px] text-muted">
        <span>找到 {{ results.length }} 篇笔记</span>
        <RouterLink to="/library" class="text-accent hover:underline">返回笔记库</RouterLink>
      </div>

      <div class="glass-card mt-3 overflow-hidden rounded-[14px]">
        <div v-if="!results.length" class="px-5 py-14 text-center text-[13px] text-faint">没有找到匹配的笔记</div>
        <button
          v-for="note in results"
          :key="note.id"
          class="flex w-full items-center gap-4 border-b border-line-soft px-5 py-4 text-left last:border-0 hover:bg-surface-2"
          @click="openNote(note)"
        >
          <Folder :size="15" class="shrink-0 text-accent" />
          <div class="min-w-0">
            <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
            <p class="mt-1 text-[11.5px] text-faint">{{ library.groupName(note.groupId) }} · {{ note.author }} · {{ note.createdAt }}</p>
          </div>
          <span
            class="ml-auto shrink-0 text-[11.5px]"
            :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
          >
            {{ statusText(note) }}
          </span>
          <ChevronRight :size="15" class="shrink-0 text-faint" />
        </button>
      </div>
    </div>
  </div>
</template>
