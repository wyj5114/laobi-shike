<script setup lang="ts">
const props = defineProps<{
  page: number
  totalPages: number
  total: number
  pageSize: number
}>()
const emit = defineEmits<{ (e: 'update:page', page: number): void }>()

function go(page: number) {
  if (page < 1 || page > props.totalPages || page === props.page) return
  emit('update:page', page)
}
</script>

<template>
  <div v-if="total > pageSize" class="mt-4 flex items-center justify-between text-[11.5px] text-muted">
    <span>共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</span>
    <div class="flex items-center gap-2">
      <button
        class="h-8 rounded-[7px] border border-line px-3 disabled:opacity-35"
        :disabled="page <= 1"
        @click="go(page - 1)"
      >
        上一页
      </button>
      <button
        class="h-8 rounded-[7px] border border-line px-3 disabled:opacity-35"
        :disabled="page >= totalPages"
        @click="go(page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>
