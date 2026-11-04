<script setup lang="ts">
import { useRoute } from 'vue-router'
import { BookOpen, Clapperboard, ListChecks, Plus, Settings, ArrowUpRight, Leaf } from 'lucide-vue-next'
const route = useRoute()
const items = [
  { to: '/', label: '学习工作台', icon: Plus, match: (path: string) => path === '/' },
  { to: '/library', label: '我的笔记', icon: BookOpen, match: (path: string) => path.startsWith('/library') || path.startsWith('/notes') },
  { to: '/media', label: '课程视频', icon: Clapperboard, match: (path: string) => path.startsWith('/media') },
  { to: '/tasks', label: '生成任务', icon: ListChecks, match: (path: string) => path.startsWith('/tasks') },
]
</script>

<template>
  <aside class="study-sidebar">
    <RouterLink to="/" class="study-brand" aria-label="老哔拾课首页">
      <span class="study-brand-icon"><BookOpen :size="23" :stroke-width="1.7" /></span>
      <span class="sidebar-copy"><strong>老哔拾课</strong><small>让知识，慢慢生长</small></span>
    </RouterLink>
    <p class="sidebar-caption sidebar-copy">我的学习空间</p>
    <nav class="study-nav" aria-label="主导航">
      <RouterLink v-for="item in items" :key="item.to" :to="item.to" :title="item.label"
        class="study-nav-link" :class="{ active: item.match(route.path) }" :aria-current="item.match(route.path) ? 'page' : undefined">
        <component :is="item.icon" :size="19" :stroke-width="1.7" />
        <span class="sidebar-copy">{{ item.label }}</span>
        <span v-if="item.match(route.path)" class="nav-dot sidebar-copy" />
      </RouterLink>
    </nav>
    <div class="sidebar-bottom">
      <div class="sidebar-note sidebar-copy">
        <Leaf :size="20" :stroke-width="1.4" />
        <p>学一点，记一点。<br /><span>每一次积累，都算数。</span></p>
        <RouterLink to="/library">翻翻我的笔记 <ArrowUpRight :size="13" /></RouterLink>
      </div>
      <RouterLink to="/settings" class="study-nav-link" :class="{ active: route.path === '/settings' }" title="学习设置">
        <Settings :size="19" :stroke-width="1.7" /><span class="sidebar-copy">学习设置</span>
      </RouterLink>
      <div class="sidebar-profile sidebar-copy"><span>拾</span><div>我的学习空间<small>专注当下，持续积累</small></div></div>
    </div>
  </aside>
</template>