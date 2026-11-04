<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Sun } from 'lucide-vue-next'
import { useLibraryStore } from '@/stores/library'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const searchText = ref('')
const crumb = computed(() => {
  if (route.name === 'note') {
    const note = library.notes.find(n => n.id === route.params.id)
    return `笔记库 / ${note?.title || '笔记详情'}`
  }
  return (route.meta.crumb as string) || ''
})
const isNote = computed(() => route.name === 'note')

function openSearch() {
  router.push({ name: 'search', query: searchText.value.trim() ? { q: searchText.value.trim() } : {} })
}

function onGlobalKey(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openSearch()
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKey))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<template>
  <header class="glass-topbar relative flex h-14 shrink-0 items-center justify-between px-7">
    <div class="text-[13px] text-muted">
      {{ crumb }}
    </div>

    <div class="flex items-center gap-3.5">
      <div class="glass-chip flex h-8 w-[250px] items-center gap-2 rounded-[9px] px-2.5 text-[12.5px] text-faint">
        <Search :size="14" :stroke-width="1.8" />
        <input
          v-model="searchText"
          class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-faint"
          placeholder="搜索笔记"
          @keydown.enter="openSearch"
        />
        <kbd class="cursor-pointer rounded border border-line bg-surface px-1.5 py-px text-[11px] text-faint" @click="openSearch">⌘K</kbd>
      </div>
      <button class="flex h-8 w-8 items-center justify-center rounded-[9px] text-muted hover:bg-surface-2 hover:text-ink" title="主题">
        <Sun :size="17" :stroke-width="1.6" />
      </button>
    </div>

    <div v-if="isNote" class="absolute bottom-0 left-0 h-0.5 w-[38%] bg-accent/85" />
  </header>
</template>
