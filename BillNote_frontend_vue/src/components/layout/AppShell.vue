<script setup lang="ts">
import RailNav from './RailNav.vue'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-transparent text-ink">
    <RailNav />
    <div class="flex min-w-0 flex-1 flex-col bg-surface/35">
      <TopBar />
      <main class="min-h-0 flex-1 overflow-hidden">
        <slot />
      </main>
    </div>
  </div>
</template>
