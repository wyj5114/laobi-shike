<script setup lang="ts">
import { useRoute } from 'vue-router'
import { BookOpen, Clapperboard, ListChecks, Plus, Settings } from 'lucide-vue-next'

const route = useRoute()

const items = [
  { to: '/', label: '新建', icon: Plus, match: (path: string) => path === '/' },
  { to: '/library', label: '笔记库', icon: BookOpen, match: (path: string) => path.startsWith('/library') || path.startsWith('/notes') },
  { to: '/media', label: '视频区', icon: Clapperboard, match: (path: string) => path.startsWith('/media') },
  { to: '/tasks', label: '任务', icon: ListChecks, match: (path: string) => path.startsWith('/tasks') },
]
</script>

<template>
  <aside class="glass-dark flex w-16 shrink-0 flex-col items-center pb-4 pt-3.5">
    <div class="mb-5 flex h-[34px] w-[34px] items-center justify-center rounded-[10px] bg-accent font-sans text-[17px] tracking-wide text-white shadow-[0_4px_14px_rgba(37,99,235,.45)]">
      拾
    </div>

    <nav class="flex w-full flex-col items-center gap-1.5">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        :title="item.label"
        class="relative flex h-11 w-11 items-center justify-center rounded-[10px] text-rail-muted transition-colors hover:bg-white/5 hover:text-white"
        :class="item.match(route.path) ? 'bg-white/10 text-white' : ''"
      >
        <component :is="item.icon" :size="19" :stroke-width="1.6" />
      </RouterLink>
    </nav>

    <div class="mt-auto">
      <RouterLink
        to="/settings"
        title="设置"
        class="flex h-11 w-11 items-center justify-center rounded-[10px] text-rail-muted transition-colors hover:bg-white/5 hover:text-white"
      >
        <Settings :size="19" :stroke-width="1.6" />
      </RouterLink>
    </div>
  </aside>
</template>
