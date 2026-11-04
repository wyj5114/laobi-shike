<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BookOpen, ChevronDown, ChevronUp, LoaderCircle, RefreshCw, Send, Square, Trash2 } from 'lucide-vue-next'
import { api, chatAskStream } from '@/services/api'
import type { ApiChatSource, ApiModel, ApiProvider } from '@/services/api'
import StreamingMarkdown from '@/components/note/StreamingMarkdown.vue'

const props = defineProps<{ taskId: string }>()
const emit = defineEmits<{ cite: [source: ApiChatSource] }>()

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: ApiChatSource[]
}

const messages = ref<Message[]>([])
const input = ref('')
const sending = ref(false)
const indexState = ref<'idle' | 'indexing' | 'indexed' | 'failed'>('idle')
const provider = ref<ApiProvider | null>(null)
const models = ref<ApiModel[]>([])
const model = ref('')
const error = ref('')
const listEl = ref<HTMLElement | null>(null)
const expandedSources = ref<Record<number, boolean>>({})
let indexTimer: number | undefined
let abortController: AbortController | null = null

const storageKey = `shike-chat:${props.taskId}`
const HISTORY_LIMIT = 12

function formatTime(seconds = 0): string {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

function sourceLabel(source: ApiChatSource): string {
  if (source.source_type === 'markdown') return `笔记 · ${source.section_title || '正文'}`
  if (source.source_type === 'meta') return '视频信息'
  return `转写 ${formatTime(source.start_time)}–${formatTime(source.end_time)}`
}

function canCite(source: ApiChatSource): boolean {
  return source.source_type === 'transcript' || source.source_type === 'markdown'
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw) messages.value = JSON.parse(raw)
  } catch {
    messages.value = []
  }
}

function persistHistory() {
  try {
    localStorage.setItem(storageKey, JSON.stringify(messages.value.slice(-40)))
  } catch {
    // storage 满时静默失败
  }
}

watch(messages, persistHistory, { deep: true })

async function scrollBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

async function init() {
  loadHistory()
  try {
    const providers = await api.listProviders()
    const usable = providers.find(p => p.enabled && p.api_key)
    if (!usable) {
      error.value = '请先在设置中配置模型 API Key'
      return
    }
    provider.value = usable
    models.value = await api.listEnabledModels(usable.id)
    model.value = models.value[0] ? String(models.value[0].model_name ?? models.value[0].id) : ''
    await ensureIndex()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function ensureIndex() {
  try {
    const status = await api.chatStatus(props.taskId)
    indexState.value = status.status as typeof indexState.value
    if (status.status === 'idle') {
      await api.chatIndex(props.taskId)
      indexState.value = 'indexing'
    }
    if (indexState.value === 'indexing') {
      if (indexTimer) window.clearTimeout(indexTimer)
      indexTimer = window.setTimeout(ensureIndex, 2000)
    }
  } catch {
    indexState.value = 'failed'
  }
}

function retryIndex() {
  indexState.value = 'idle'
  error.value = ''
  ensureIndex()
}

async function send() {
  const question = input.value.trim()
  if (!question || sending.value) return
  if (!provider.value || !model.value) {
    error.value = '请先选择模型'
    return
  }

  const history = messages.value
    .slice(-HISTORY_LIMIT)
    .map(m => ({ role: m.role, content: m.content }))

  messages.value.push({ role: 'user', content: question })
  const assistantIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '', sources: [] })
  input.value = ''
  sending.value = true
  error.value = ''
  await scrollBottom()

  abortController = new AbortController()
  try {
    await chatAskStream(
      {
        task_id: props.taskId,
        question,
        history,
        provider_id: provider.value.id,
        model_name: model.value,
      },
      {
        onSources: sources => {
          if (messages.value[assistantIndex]) messages.value[assistantIndex].sources = sources
        },
        onToken: delta => {
          if (messages.value[assistantIndex]) messages.value[assistantIndex].content += delta
          scrollBottom()
        },
        onDone: answer => {
          if (messages.value[assistantIndex] && answer) messages.value[assistantIndex].content = answer
        },
        onError: message => {
          error.value = message
        },
      },
      abortController.signal,
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      error.value = e instanceof Error ? e.message : String(e)
    }
  } finally {
    if (!messages.value[assistantIndex]?.content) {
      messages.value.splice(assistantIndex, 1)
    }
    sending.value = false
    abortController = null
    await scrollBottom()
  }
}

function stop() {
  abortController?.abort()
  sending.value = false
  error.value = '已停止生成'
}

async function retryFrom(index: number) {
  if (sending.value) return
  const before = messages.value.slice(0, index)
  const userIndex = before.map(m => m.role).lastIndexOf('user')
  if (userIndex < 0) return
  const question = before[userIndex].content
  messages.value = before.slice(0, userIndex)
  input.value = question
  await send()
}

function onKeydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function clearChat() {
  if (!messages.value.length || !window.confirm('清空这篇笔记的对话记录？')) return
  messages.value = []
  expandedSources.value = {}
  localStorage.removeItem(storageKey)
}

onMounted(init)
onBeforeUnmount(() => {
  if (indexTimer) window.clearTimeout(indexTimer)
  abortController?.abort()
})
</script>

<template>
  <div class="flex h-[640px] flex-col rounded-[12px] border border-line bg-surface">
    <div class="flex items-center justify-between border-b border-line px-5 py-3">
      <div>
        <p class="text-[13.5px] font-medium">问这篇笔记</p>
        <p class="mt-0.5 text-[11.5px] text-faint">
          {{ indexState === 'indexed' ? '已建立索引' : indexState === 'indexing' ? '正在建立索引…' : indexState === 'failed' ? '索引失败，将尝试直接回答' : '准备索引' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="indexState === 'failed'" class="text-[11px] text-accent hover:underline" @click="retryIndex">重试索引</button>
        <select v-if="models.length" v-model="model" class="h-7 max-w-[180px] rounded-[6px] border border-line bg-surface-2 px-1.5 text-[11px] text-muted outline-none">
          <option v-for="item in models" :key="String(item.id)" :value="String(item.model_name ?? item.id)">
            {{ item.model_name ?? item.id }}
          </option>
        </select>
        <button class="rounded-md p-1.5 text-faint hover:bg-surface-2 hover:text-ink" title="清空对话" @click="clearChat">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>

    <div ref="listEl" class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
      <div v-if="!messages.length" class="flex h-full items-center justify-center text-[13px] text-faint">
        基于笔记与转写内容提问，例如「这节课的重点是什么？」
      </div>
      <div v-for="(message, idx) in messages" :key="idx" class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
        <div
          class="max-w-[80%] rounded-[12px] px-4 py-2.5 text-[13px] leading-6"
          :class="message.role === 'user' ? 'bg-accent text-white' : 'bg-surface-2 text-ink-2'"
        >
          <StreamingMarkdown
            v-if="message.role === 'assistant'"
            :content="message.content"
            :streaming="sending && idx === messages.length - 1"
          />
          <span v-else class="whitespace-pre-wrap">{{ message.content }}</span>

          <div v-if="message.role === 'assistant' && !sending" class="mt-1 flex items-center gap-3">
            <button class="flex items-center gap-1 text-[10.5px] text-faint hover:text-ink" @click="retryFrom(idx)">
              <RefreshCw :size="11" /> 重新回答
            </button>
          </div>

          <div v-if="message.sources?.length" class="mt-2 border-t border-line/60 pt-1.5">
            <button class="flex items-center gap-1 text-[11px] text-faint hover:text-ink" @click="expandedSources[idx] = !expandedSources[idx]">
              <BookOpen :size="11" /> 引用来源 ({{ message.sources.length }})
              <ChevronUp v-if="expandedSources[idx]" :size="11" />
              <ChevronDown v-else :size="11" />
            </button>
            <div v-if="expandedSources[idx]" class="mt-1.5 space-y-1">
              <button
                v-for="(source, sIdx) in message.sources"
                :key="sIdx"
                class="block w-full rounded border border-line bg-surface px-2 py-1.5 text-left"
                :class="canCite(source) ? 'cursor-pointer hover:border-accent' : ''"
                @click="canCite(source) && emit('cite', source)"
              >
                <span class="text-[10.5px] font-medium" :class="canCite(source) ? 'text-accent' : 'text-muted'">
                  {{ sourceLabel(source) }}
                </span>
                <span
                  class="mt-0.5 block overflow-hidden text-[10px] leading-4 text-muted/80"
                  style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical"
                >
                  {{ source.text }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="sending" class="flex items-center gap-2 text-[12px] text-faint">
        <LoaderCircle :size="14" class="animate-spin" /> 正在思考…
      </div>
    </div>

    <p v-if="error" class="px-5 pb-2 text-[11.5px] text-accent">{{ error }}</p>

    <div class="flex items-end gap-2 border-t border-line p-3">
      <textarea
        v-model="input"
        rows="1"
        class="h-10 min-w-0 flex-1 resize-none rounded-[9px] border border-line bg-surface-2 px-3 py-2.5 text-[13px] leading-5 outline-none focus:border-accent"
        placeholder="问点什么… Enter 发送，Shift+Enter 换行"
        @keydown="onKeydown"
      />
      <button v-if="sending" class="flex h-10 w-10 items-center justify-center rounded-[9px] border border-line text-muted hover:bg-surface-2" title="停止生成" @click="stop">
        <Square :size="14" />
      </button>
      <button v-else class="flex h-10 w-10 items-center justify-center rounded-[9px] bg-accent text-white disabled:opacity-40" :disabled="sending" @click="send">
        <Send :size="16" />
      </button>
    </div>
  </div>
</template>
