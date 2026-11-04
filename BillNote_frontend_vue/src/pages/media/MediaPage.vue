<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Clapperboard, FileAudio, Image as ImageIcon, Trash2 } from 'lucide-vue-next'
import { api, type ApiMedia } from '@/services/api'

const items = ref<ApiMedia[]>([])
const totalSize = ref(0)
const selected = ref<ApiMedia | null>(null)
const loading = ref(false)
const message = ref('')

const selectedKind = computed(() => selected.value?.kind)

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const result = await api.listMedia()
    items.value = result.items
    totalSize.value = result.total_size
    if (selected.value && !items.value.find(item => item.path === selected.value?.path)) selected.value = null
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function remove(item: ApiMedia) {
  try {
    await api.deleteMedia(item.path)
    if (selected.value?.path === item.path) selected.value = null
    await load()
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function cleanAll() {
  if (!window.confirm('确定清理全部视频、音频和截图吗？笔记本身不会删除。')) return
  try {
    const result = await api.cleanMedia()
    message.value = `已清理 ${result.deleted} 个文件，释放 ${formatSize(result.freed)}`
    selected.value = null
    await load()
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

onMounted(load)
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="page-frame media-page">
      <div class="page-heading flex items-end justify-between">
        <div>
          <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Media</p>
          <h1 class="mt-2 text-[30px] font-semibold tracking-[-0.025em]">视频区</h1>
          <p class="mt-2 text-[13px] text-muted">下载的音频、视频和截图缓存，删除不影响笔记内容。</p>
        </div>
        <div class="text-right">
          <p class="text-[12px] text-faint">共 {{ items.length }} 个文件</p>
          <p class="mt-1 text-[15px] font-medium">{{ formatSize(totalSize) }}</p>
          <button class="mt-3 h-9 rounded-[8px] border border-line px-3 text-[12px] text-muted hover:bg-surface-2" @click="cleanAll">
            清理全部
          </button>
        </div>
      </div>

      <p v-if="message" class="mt-4 text-[12px] text-accent">{{ message }}</p>

      <div v-if="selected" class="mt-6 overflow-hidden rounded-[14px] border border-line bg-black">
        <video v-if="selectedKind === 'video'" :src="selected.url" controls class="max-h-[430px] w-full" />
        <audio v-else-if="selectedKind === 'audio'" :src="selected.url" controls class="w-full p-6" />
        <img v-else :src="selected.url" class="max-h-[430px] w-full object-contain" alt="" />
      </div>

      <div class="glass-card mt-6 overflow-hidden rounded-[14px]">
        <div v-if="loading" class="p-8 text-center text-[13px] text-faint">正在读取媒体文件…</div>
        <div v-else-if="!items.length" class="p-10 text-center text-[13px] text-faint">还没有缓存文件</div>
        <button
          v-for="item in items"
          :key="item.path"
          class="flex w-full items-center gap-4 border-b border-line-soft px-4 py-3.5 text-left last:border-0 hover:bg-surface-2"
          @click="selected = item"
        >
          <Clapperboard v-if="item.kind === 'video'" :size="16" class="text-accent" />
          <FileAudio v-else-if="item.kind === 'audio'" :size="16" class="text-accent" />
          <ImageIcon v-else :size="16" class="text-accent" />
          <div class="min-w-0">
            <p class="truncate text-[13.5px] font-medium">{{ item.name }}</p>
            <p class="mt-0.5 text-[11px] text-faint">{{ formatDate(item.modified) }}</p>
          </div>
          <span class="ml-auto text-[11.5px] text-muted">{{ formatSize(item.size) }}</span>
          <button class="rounded-md p-1.5 text-faint hover:bg-red-50 hover:text-red-500" title="删除" @click.stop="remove(item)">
            <Trash2 :size="14" />
          </button>
        </button>
      </div>
    </div>
  </div>
</template>
