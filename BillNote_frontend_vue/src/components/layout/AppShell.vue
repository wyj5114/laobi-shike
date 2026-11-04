<script setup lang="ts">
import RailNav from './RailNav.vue'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="app-shell flex h-screen overflow-hidden text-ink">
    <RailNav />
    <div class="app-content flex min-w-0 flex-1 flex-col">
      <TopBar />
      <main class="app-main min-h-0 flex-1 overflow-hidden">
        <slot />
      </main>
    </div>
  </div>
</template>
