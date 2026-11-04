<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ExternalLink, RotateCcw, Share2, Trash2 } from 'lucide-vue-next'
import { api, type ApiChatSource, type ApiNote, type ApiTranscriptSegment } from '@/services/api'
import { useLibraryStore } from '@/stores/library'
import { cleanNoteTitle } from '@/utils/note'
import { createMarkdownRenderer, extractHeadings } from '@/utils/markdown'
import { mockNote } from '@/mock/note'

const MarkmapViewAsync = defineAsyncComponent(() => import('@/components/note/MarkmapView.vue'))
const ChatPanelAsync = defineAsyncComponent(() => import('@/components/note/ChatPanel.vue'))

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const md = createMarkdownRenderer()

const note = ref<ApiNote | null>(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref(String(route.params.tab || 'note'))
const coverFailed = ref(false)

const tabs = computed(() => [
  { key: 'note', label: '笔记' },
  { key: 'organized', label: '整理', count: organized.value.length },
  { key: 'mindmap', label: '思维导图' },
  { key: 'chat', label: 'AI 问答' },
])

const displayTitle = computed(() => cleanNoteTitle(note.value?.title || ''))
const author = computed(() => note.value?.audio_meta?.raw_info?.uploader || 'B 站')
const duration = computed(() => formatDuration(note.value?.duration || note.value?.audio_meta?.duration || 0))
const createdAt = computed(() => formatDate(note.value?.created_at || null))
const groupName = computed(() => library.groupName(note.value?.group_id ?? null))
const markdown = computed(() => note.value?.markdown || '')
const headings = computed(() => extractHeadings(markdown.value))
const html = computed(() => md.render(markdown.value))

const segments = computed<ApiTranscriptSegment[]>(() => note.value?.transcript?.segments || [])

const organized = computed(() => {
  const groups: Array<{ start: number; end: number; text: string }> = []
  let buffer: string[] = []
  let start = 0
  let end = 0
  let chars = 0
  let last = ''

  const flush = () => {
    if (!buffer.length) return
    groups.push({ start, end, text: buffer.join('') })
    buffer = []
    chars = 0
  }

  for (const segment of segments.value) {
    const text = cleanFiller(segment.text)
    if (!text || text === last) continue
    last = text
    if (!buffer.length) start = segment.start
    buffer.push(text)
    end = segment.end
    chars += text.length
    if (chars >= 180 || buffer.length >= 5) flush()
  }
  flush()
  return groups
})

function cleanFiller(text: string): string {
  return text
    .replace(
      /(嗯+|啊+|呃+|额+|哎+|哎呀|那个|那么|这个|就是说|然后呢|对吧|是吧|这个这个|就是就是|其实|反正|怎么说呢|你知道吧)/g,
      '',
    )
    .replace(/[，,]\s*[，,]+/g, '，')
    .replace(/^[，。！？、；：\s]+/, '')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatDate(value: string | null): string {
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function openOriginal() {
  const id = note.value?.video_id?.split('_')[0]
  if (id) window.open(`https://www.bilibili.com/video/${id}`, '_blank')
}

function exportMarkdown() {
  if (!markdown.value) return
  const blob = new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${displayTitle.value.replace(/[\\/:*?"<>|]/g, '_')}.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function deleteNote() {
  if (!note.value || !window.confirm('确定删除这篇笔记吗？笔记正文、转写和缓存都会删除。')) return
  try {
    await api.deleteNote(note.value.id)
    await library.load()
    router.push('/library')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function scrollToHeading(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function jumpToSource(source: ApiChatSource) {
  if (source.source_type === 'markdown') {
    activeTab.value = 'note'
    return
  }
  if (source.start_time == null) return
  activeTab.value = 'organized'
  nextTick(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-org-start]'))
    const target = nodes.filter(node => Number(node.dataset.orgStart) <= source.start_time!).pop() || nodes[0]
    if (!target) return
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    target.classList.add('ring-2', 'ring-accent/30')
    window.setTimeout(() => target.classList.remove('ring-2', 'ring-accent/30'), 1600)
  })
}

async function loadNote() {
  loading.value = true
  error.value = ''
  coverFailed.value = false
  try {
    note.value = await api.getNote(String(route.params.id))
    route.meta.crumb = `笔记库 / ${note.value.title}`
  } catch (e) {
    if (String(route.params.id) === 'demo') {
      note.value = {
        id: 'demo',
        video_id: 'BV1xx411c7mD',
        platform: 'bilibili',
        title: mockNote.title,
        duration: 2538,
        cover_url: null,
        group_id: null,
        status: 'SUCCESS',
        created_at: null,
        updated_at: null,
        markdown: mockNote.markdown,
        transcript: { segments: [] },
      }
    } else {
      error.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadNote)
onMounted(() => library.load())
watch(() => route.params.id, loadNote)
watch(() => route.params.tab, tab => {
  activeTab.value = String(tab || 'note')
})
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="glass-paper mx-auto mb-10 mt-6 w-[1000px] rounded-[18px] px-7 pb-24 pt-8">
      <div v-if="loading" class="flex h-[300px] items-center justify-center text-[13px] text-faint">正在加载笔记…</div>
      <div v-else-if="error" class="flex h-[300px] items-center justify-center text-[13px] text-accent">{{ error }}</div>

      <template v-else>
        <div class="flex items-start gap-5 border-b border-line pb-5">
          <div
            class="relative h-[94px] w-[168px] shrink-0 overflow-hidden rounded-lg bg-[linear-gradient(135deg,var(--color-rail)_0%,var(--color-rail-2)_55%,var(--color-accent)_100%)] bg-cover bg-center"
            :style="note?.cover_url && !coverFailed ? { backgroundImage: `url(${note.cover_url})` } : {}"
          >
            <img
              v-if="note?.cover_url && !coverFailed"
              :src="note.cover_url"
              class="absolute inset-0 h-full w-full object-cover"
              alt=""
              @error="coverFailed = true"
            />
            <div v-if="!note?.cover_url || coverFailed" class="absolute left-1/2 top-1/2 flex h-[34px] w-[34px] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-surface/90">
              <span class="ml-0.5 block h-0 w-0 border-y-[6px] border-l-[10px] border-y-transparent border-l-ink" />
            </div>
          </div>

          <div class="min-w-0 flex-1">
            <h1 class="text-[26px] font-semibold leading-[1.35] tracking-[-0.02em]">{{ displayTitle }}</h1>
            <div class="mt-2 flex items-center gap-2 text-[12.5px] text-muted">
              <span>{{ author }}</span>
              <span class="h-[3px] w-[3px] rounded-full bg-line" />
              <span>{{ duration }}</span>
              <span class="h-[3px] w-[3px] rounded-full bg-line" />
              <span>{{ createdAt }} 生成</span>
            </div>
            <div class="mt-2.5 flex gap-1.5">
              <span class="rounded-[5px] border border-accent/25 bg-accent-soft px-1.5 py-0.5 text-[11px] text-accent">
                分组 · {{ groupName }}
              </span>
              <span class="rounded-[5px] border border-line bg-surface-2 px-1.5 py-0.5 text-[11px] text-muted">B 站</span>
            </div>
          </div>

          <div class="ml-auto flex items-start gap-2">
            <button class="h-[34px] rounded-md border border-line bg-surface px-3 text-[12.5px] hover:bg-surface-2" @click="exportMarkdown">
              <Share2 :size="13" class="mr-1 inline" /> 导出 Markdown
            </button>
            <button class="h-[34px] rounded-md border border-line bg-surface px-3 text-[12.5px] hover:bg-surface-2" @click="router.push(`/tasks/${note?.id}`)">
              <RotateCcw :size="13" class="mr-1 inline" /> 重新生成
            </button>
            <button class="h-[34px] rounded-md bg-accent px-3 text-[12.5px] text-white hover:bg-[#1d4ed8]" @click="openOriginal">
              <ExternalLink :size="13" class="mr-1 inline" /> 打开原视频
            </button>
            <button
              class="flex h-[34px] w-8 items-center justify-center rounded-md text-muted hover:bg-red-50 hover:text-red-500"
              title="删除笔记"
              @click="deleteNote"
            >
              <Trash2 :size="15" />
            </button>
          </div>
        </div>

        <div class="flex gap-7 border-b border-line pt-4">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="relative pb-3 text-[13.5px]"
            :class="activeTab === tab.key ? 'font-medium text-ink' : 'text-muted'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
            <span v-if="tab.count" class="ml-1 text-[11px] text-faint">{{ tab.count }}</span>
            <span v-if="activeTab === tab.key" class="absolute inset-x-0 -bottom-px h-0.5 bg-accent" />
          </button>
        </div>

        <div v-if="activeTab === 'note'" class="flex gap-11 pt-7">
          <aside class="w-[180px] shrink-0">
            <h4 class="mb-3 text-[11px] uppercase tracking-[.14em] text-faint">目录</h4>
            <button
              v-for="heading in headings"
              :key="heading.id"
              class="block w-full border-l border-line py-1.5 pr-2 text-left text-[12px] leading-[1.55] text-muted transition-colors hover:border-accent hover:text-accent"
              :class="heading.level === 1 ? 'pl-2.5 font-medium text-ink' : heading.level === 2 ? 'pl-2.5' : 'pl-5 text-[11.5px]'"
              @click="scrollToHeading(heading.id)"
            >
              <span v-html="md.renderInline(heading.text)" />
            </button>
            <p v-if="!headings.length" class="border-l border-line py-1.5 pl-2.5 text-[12px] text-faint">正文</p>
          </aside>
          <article v-if="markdown" class="article-body w-[720px] pb-20" v-html="html" />
          <div v-else class="flex h-[300px] w-[720px] items-center justify-center text-[13px] text-faint">这篇笔记还没有正文</div>
        </div>

        <div v-else-if="activeTab === 'organized'" class="pt-7">
          <div class="mb-4 flex items-baseline justify-between">
            <div>
              <h3 class="text-[16px] font-semibold">整理</h3>
              <p class="mt-1 text-[12px] text-muted">转写原话整理 · 已去除口头废话</p>
            </div>
            <span class="text-[11.5px] text-faint">{{ segments.length }} 段原话</span>
          </div>
          <div v-if="organized.length" class="space-y-4">
            <div v-for="(group, idx) in organized" :key="idx" :data-org-start="group.start" class="grid grid-cols-[56px_1fr] gap-4 rounded-md border-b border-line-soft pb-4 transition-shadow">
              <span class="pt-0.5 font-mono text-[11.5px] text-faint">{{ formatTime(group.start) }}</span>
              <p class="text-[15px] leading-[1.8] text-ink-2">{{ group.text }}</p>
            </div>
          </div>
          <div v-else class="flex h-[200px] items-center justify-center text-[13px] text-faint">暂无转写内容</div>
        </div>

        <div v-else-if="activeTab === 'mindmap'" class="h-[620px] pt-7">
          <MarkmapViewAsync :markdown="markdown" />
        </div>

        <div v-else class="pt-7">
          <ChatPanelAsync :task-id="String(note?.id || '')" @cite="jumpToSource" />
        </div>
      </template>
    </div>
  </div>
</template>
