<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ArrowUpRight, BookOpen, Check, ChevronDown, ChevronRight, Clock3, FileDown, Folder, Leaf, Link2, LoaderCircle, Pencil, Search, Settings2, Sparkles, X } from 'lucide-vue-next'
import { useLibraryStore, type NoteSummary } from '@/stores/library'
import { api, type ApiCollection, type ApiModel, type ApiProvider } from '@/services/api'
import '@/design/workspace.css'

const router = useRouter()
const library = useLibraryStore()
const completedCount = computed(() => library.notes.filter(note => note.status === 'done').length)
const activeCount = computed(() => library.notes.filter(note => note.status === 'running' || note.status === 'pending').length)
const noteQuery = ref('')
const noteFilter = ref('all')
const noteFilters = computed(() => [
  { id: 'all', label: '全部', count: library.notes.length },
  { id: 'done', label: '已完成', count: completedCount.value },
  { id: 'active', label: '进行中', count: activeCount.value },
  { id: 'failed', label: '需处理', count: library.notes.filter(note => note.status === 'failed').length },
])
const filteredNotes = computed(() => {
  const query = noteQuery.value.trim().toLowerCase()
  return library.sortedNotes.filter(note =>
    (!query || `${note.title} ${note.author}`.toLowerCase().includes(query)) &&
    (noteFilter.value === 'all' || (noteFilter.value === 'active' ? ['pending', 'running'].includes(note.status) : note.status === noteFilter.value)),
  )
})
const visibleGroups = computed(() => library.sortedGroups.filter(group =>
  filteredNotes.value.some(note => note.groupId === group.id) || (!noteQuery.value.trim() && noteFilter.value === 'all'),
))
const filteredUngrouped = computed(() => filteredNotes.value.filter(note => note.groupId === null))
watch([noteQuery, noteFilter], () => {
  for (const group of visibleGroups.value) library.collapsed[group.id] = false
  library.collapsed.ungrouped = false
})
const today = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long', timeZone: 'Asia/Shanghai' }).format(new Date())
const urlInput = ref<HTMLInputElement | null>(null)
const submitting = ref(false)
const configLoading = ref(true)
const transcriberLabel = ref('正在读取')
const transcriberReady = ref<boolean | null>(null)

async function loadTranscriberStatus() {
  try {
    const config = await api.getTranscriberConfig()
    const engine = config.available_types.find(item => item.value === config.transcriber_type)?.label ?? config.transcriber_type
    transcriberLabel.value = engine
    if (['fast-whisper', 'mlx-whisper'].includes(config.transcriber_type)) {
      const statuses = await api.getTranscriberModelsStatus()
      const models = config.transcriber_type === 'mlx-whisper' ? statuses.mlx_whisper : statuses.whisper
      transcriberReady.value = models.some(item => item.model_size === config.whisper_model_size && item.downloaded)
      transcriberLabel.value = `${engine} · ${config.whisper_model_size}`
    } else {
      transcriberReady.value = true
    }
  } catch {
    transcriberReady.value = null
    transcriberLabel.value = '暂时无法读取，请检查设置'
  }
}

async function pasteLink() {
  try {
    url.value = (await navigator.clipboard.readText()).trim()
    urlInput.value?.focus()
  } catch {
    submitted.value = '无法读取剪贴板，请在输入框按 Ctrl + V 粘贴。'
    urlInput.value?.focus()
  }
}

const url = ref(new URLSearchParams(window.location.search).get('url') || '')
const submitted = ref('')
const newGroupOpen = ref(false)
const newGroupName = ref('')
const newGroupError = ref('')
const editingGroupId = ref('')
const editingGroupName = ref('')
const providers = ref<ApiProvider[]>([])
const selectedProvider = ref<ApiProvider | null>(null)
const selectedModel = ref('')
const availableModels = ref<ApiModel[]>([])
const configError = ref('')
const collection = ref<ApiCollection | null>(null)
const collectionLoading = ref(false)
const collectionError = ref('')
const selectedCollectionIds = ref<string[]>([])
const rangeStart = ref(1)
const rangeEnd = ref(1)
const batchGroupId = ref('')
const batchConcurrency = ref(1)
const batchBusy = ref(false)
const batchProgress = ref('')
let collectionTimer: number | undefined

const isBilibili = computed(() => /(bilibili\.com\/video\/|b23\.tv\/)/i.test(url.value))
let refreshTimer: number | undefined

watch(url, value => {
  submitted.value = ''
  if (collectionTimer) window.clearTimeout(collectionTimer)
  collection.value = null
  collectionLoading.value = false
  selectedCollectionIds.value = []
  collectionError.value = ''
  if (!/(bilibili\.com\/video\/|b23\.tv\/)/i.test(value)) return
  collectionTimer = window.setTimeout(loadCollection, 700)
})

onMounted(async () => {
  await Promise.all([library.load(), loadModelConfig(), loadTranscriberStatus()])
  if (isBilibili.value) void loadCollection()
  refreshTimer = window.setInterval(() => library.load(), 5000)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
  if (collectionTimer) window.clearTimeout(collectionTimer)
})

async function loadModelConfig() {
  configLoading.value = true
  configError.value = ''
  try {
    providers.value = await api.listProviders()
    const usable = providers.value.find(p => p.enabled && p.api_key)
    if (!usable) {
      configError.value = '还没有配置模型 API Key'
      return
    }
    const saved = await api.listEnabledModels(usable.id)
    if (saved.length) {
      availableModels.value = saved
      const preferred = saved.find(item => item.model_name === 'cn:glm-5.3-flash') ?? saved[0]
      selectedProvider.value = usable
      selectedModel.value = String(preferred.model_name ?? preferred.id)
      configError.value = ''
      return
    }

    const result = await api.listModels(usable.id)
    availableModels.value = result.models ?? []
    const preferred = result.models?.find(item => String(item.id) === 'cn:glm-5.3-flash')
    const model = preferred
      ? String(preferred.id)
      : result.models?.[0]
        ? String(result.models[0].model_name ?? result.models[0].id)
        : ''
    if (!model) {
      configError.value = result.error || '该供应商下没有可用模型'
      return
    }
    selectedProvider.value = usable
    selectedModel.value = model
    configError.value = ''
  } catch (error) {
    configError.value = error instanceof Error ? error.message : String(error)
  } finally {
    configLoading.value = false
  }
}
const showError = computed(() => url.value.trim().length > 0 && !isBilibili.value)

const videoId = computed(() => {
  const match = url.value.match(/(BV[a-zA-Z0-9]+)/)
  return match?.[1] ?? 'b23.tv 短链接'
})

const formats = ['目录', 'AI 总结']
const styles = [
  { label: '详细', value: 'detailed' },
  { label: '精简', value: 'minimal' },
  { label: '学术', value: 'academic' },
  { label: '教程', value: 'tutorial' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '生活向', value: 'life_journal' },
  { label: '任务导向', value: 'task_oriented' },
  { label: '商业风格', value: 'business' },
  { label: '会议纪要', value: 'meeting_minutes' },
  { label: '课程笔记（Skill）', value: 'skill' },
]
const selectedStyle = ref('detailed')

const collectedItems = computed(() => collection.value?.items ?? [])
const selectedCollectionItems = computed(() =>
  collectedItems.value.filter(item => selectedCollectionIds.value.includes(item.video_id)),
)

async function loadCollection() {
  if (!isBilibili.value) return
  const requestedUrl = url.value
  collectionLoading.value = true
  collectionError.value = ''
  try {
    const data = await api.getCollection(requestedUrl)
    if (requestedUrl !== url.value) return
    collection.value = data
    rangeStart.value = 1
    rangeEnd.value = data.total
  } catch (error) {
    if (requestedUrl !== url.value) return
    collectionError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (requestedUrl === url.value) collectionLoading.value = false
  }
}

function toggleCollectionItem(id: string) {
  selectedCollectionIds.value = selectedCollectionIds.value.includes(id)
    ? selectedCollectionIds.value.filter(item => item !== id)
    : [...selectedCollectionIds.value, id]
}

function selectAllCollection() {
  if (!collection.value) return
  selectedCollectionIds.value = collection.value.items.filter(item => !item.generated).map(item => item.video_id)
}

function selectUngenerated() {
  if (!collection.value) return
  selectedCollectionIds.value = collection.value.items.filter(item => !item.generated).map(item => item.video_id)
}

function clearCollectionSelection() {
  selectedCollectionIds.value = []
}

function applyCollectionRange() {
  if (!collection.value) return
  const start = Math.max(1, Math.min(rangeStart.value, collection.value.total))
  const end = Math.max(start, Math.min(rangeEnd.value, collection.value.total))
  rangeStart.value = start
  rangeEnd.value = end
  selectedCollectionIds.value = collection.value.items
    .slice(start - 1, end)
    .filter(item => !item.generated)
    .map(item => item.video_id)
}

async function generateCollection() {
  if (!collection.value || !selectedCollectionItems.value.length || batchBusy.value) return
  if (!selectedProvider.value || !selectedModel.value) {
    batchProgress.value = '请先在设置中配置模型'
    return
  }
  batchBusy.value = true
  batchProgress.value = `0 / ${selectedCollectionItems.value.length}`
  try {
    let groupId = batchGroupId.value || null
    if (!groupId) {
      const name = collection.value.title.slice(0, 30) || '课程合集'
      const existing = library.groups.find(group => group.name === name)
      groupId = existing?.id ?? (await api.createGroup(name)).id
      batchGroupId.value = groupId
      await library.load()
    }
    let done = 0
    const result = await api.generateBatch({
      items: selectedCollectionItems.value.map(item => ({ video_url: item.url, title: item.title })),
      platform: 'bilibili',
      quality: 'medium',
      model_name: selectedModel.value,
      provider_id: selectedProvider.value.id,
      style: selectedStyle.value,
      format: formats,
      group_id: groupId || undefined,
      batch_concurrency: batchConcurrency.value,
    })
    done = result.count
    batchProgress.value = `已加入任务队列：${done} 集 · 并发 ${result.concurrency}`
    await library.load()
    router.push('/tasks')
  } catch (error) {
    batchProgress.value = error instanceof Error ? error.message : String(error)
  } finally {
    batchBusy.value = false
  }
}

async function submit() {
  if (!isBilibili.value || submitting.value) return
  if (!selectedProvider.value || !selectedModel.value) {
    submitted.value = configError.value || '请先在设置中配置模型 API Key'
    return
  }
  submitting.value = true
  submitted.value = ''
  try {
    const { task_id } = await api.generateNote({
      video_url: url.value,
      platform: 'bilibili',
      quality: 'medium',
      model_name: selectedModel.value,
      provider_id: selectedProvider.value.id,
      style: selectedStyle.value,
      format: formats,
    })
    library.addPendingNote({
      id: task_id,
      title: '正在解析 B 站视频…',
      author: '哔站拾课',
      duration: '--:--',
      style: '详细风格',
      groupId: null,
    })
    url.value = ''
    router.push(`/tasks/${task_id}`)
  } catch (error) {
    submitted.value = error instanceof Error ? error.message : String(error)
  } finally {
    submitting.value = false
  }
}

async function createGroup() {
  const group = await library.createGroup(newGroupName.value)
  if (!group) {
    newGroupError.value = newGroupName.value.trim() ? '分组创建失败（可能重名）' : '请输入分组名'
    return
  }
  newGroupName.value = ''
  newGroupError.value = ''
  newGroupOpen.value = false
}

function openNote(note: NoteSummary) {
  router.push(note.status === 'done' ? `/notes/${note.id}` : `/tasks/${note.id}`)
}

function startRename(group: { id: string; name: string }) {
  editingGroupId.value = group.id
  editingGroupName.value = group.name
}

async function commitRename() {
  if (!editingGroupId.value) return
  const id = editingGroupId.value
  const name = editingGroupName.value
  editingGroupId.value = ''
  editingGroupName.value = ''
  await library.renameGroup(id, name)
}

function cancelRename() {
  editingGroupId.value = ''
  editingGroupName.value = ''
}

function moveNote(note: NoteSummary, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  library.moveNote(note.id, value || null)
}

async function downloadGroup(groupId: string | null, name: string) {
  try {
    const blob = await api.exportGroup(groupId ?? 'ungrouped')
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${name.replace(/[\\/:*?"<>|]/g, '_')}-笔记.zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    submitted.value = error instanceof Error ? error.message : String(error)
  }
}

function statusLabel(status: NoteSummary['status']) {
  return status === 'done' ? '已完成' : status === 'running' ? '进行中' : status === 'pending' ? '未开始' : '失败'
}
</script>

<template>
  <div class="study-home h-full overflow-y-auto">
    <div class="study-workspace workspace-v2">
      <div class="study-welcome">
        <div>
          <p class="study-eyebrow"><span /> 我的学习工作台</p>
          <h1>把今天的好奇，变成明天的收获。</h1>
          <p class="study-intro">从一节好课开始，让每一点新知都有迹可循。</p>
        </div>
        <span class="workspace-date"><Clock3 :size="14" /> {{ today }}</span>
      </div>

      <div class="workspace-stats" aria-label="学习概览">
        <RouterLink to="/library" class="workspace-stat"><span class="stat-icon"><BookOpen :size="19" /></span><div><span>已积累笔记</span><strong>{{ completedCount }}<small>篇</small></strong></div><ArrowUpRight :size="15" /></RouterLink>
        <RouterLink to="/tasks" class="workspace-stat"><span class="stat-icon stat-icon-warm"><Clock3 :size="19" /></span><div><span>进行中任务</span><strong>{{ activeCount }}<small>个</small></strong></div><ArrowUpRight :size="15" /></RouterLink>
        <RouterLink to="/library" class="workspace-stat"><span class="stat-icon stat-icon-neutral"><Folder :size="19" /></span><div><span>课程分组</span><strong>{{ library.groups.length }}<small>组</small></strong></div><ArrowUpRight :size="15" /></RouterLink>
      </div>

      <div class="study-content-grid">
      <div class="min-w-0">

      <!-- 输入台 -->
      <div class="glass-card study-import rounded-[16px] p-5">
        <div class="import-heading"><span class="import-icon"><Sparkles :size="19" /></span><div><h2>开启一段新学习</h2><p>把视频里的知识，整理成可以反复翻阅的笔记</p></div><span class="import-badge">支持单集 / 合集</span></div>
        <div class="study-url-field flex items-center gap-3 px-3 py-1.5">
          <Link2 :size="18" :stroke-width="1.7" class="shrink-0 text-faint" />
          <input
            v-model="url"
            ref="urlInput"
            class="h-10 min-w-0 flex-1 bg-transparent text-[15.5px] text-ink outline-none placeholder:text-faint"
            placeholder="粘贴 bilibili.com 或 b23.tv 课程链接…"
            aria-label="B 站课程链接"
            :aria-invalid="showError"
            aria-describedby="workspace-link-help"
            :disabled="submitting"
            @keydown.enter="submit"
          />
          <button v-if="url && !submitting" class="workspace-clear" aria-label="清空课程链接" @click="url = ''; urlInput?.focus()"><X :size="15" /></button>
          <button v-if="!url" class="workspace-paste" @click="pasteLink">粘贴</button>
          <button
            class="workspace-generate"
            :class="isBilibili ? 'bg-accent text-white hover:opacity-90' : 'cursor-not-allowed bg-surface-2 text-muted'"
            :disabled="!isBilibili || submitting || configLoading || !selectedModel"
            @click="submit"
          >
            <LoaderCircle v-if="submitting" :size="15" class="workspace-spinner" /><Sparkles v-else :size="15" />
            {{ submitting ? '提交中…' : '生成笔记' }}
          </button>
        </div>

        <div class="workspace-options mt-3 flex flex-wrap items-center gap-2 pb-1.5 pt-2.5">
          <label class="glass-chip flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-muted">
            模型 ·
            <select v-model="selectedModel" aria-label="生成模型" :disabled="configLoading || submitting" class="max-w-[190px] bg-transparent text-[12px] text-ink outline-none">
              <option v-if="!availableModels.length" value="">{{ configLoading ? '读取中…' : '未配置' }}</option>
              <option v-for="item in availableModels" :key="String(item.id)" :value="String(item.model_name ?? item.id)">
                {{ item.model_name ?? item.id }}
              </option>
            </select>
          </label>
          <label class="glass-chip flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-muted">
            风格 ·
            <select v-model="selectedStyle" aria-label="笔记风格" :disabled="submitting" class="bg-transparent text-[12px] text-ink outline-none">
              <option v-for="item in styles" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <span class="glass-chip rounded-md px-2 py-1 text-[12px] text-muted">格式 · {{ formats.join(' + ') }}</span>
        </div>
        <p id="workspace-link-help" class="workspace-input-hint"><Check :size="13" /> 支持 B 站视频及多 P 课程，粘贴后自动识别合集。</p>

        <div v-if="configError" class="workspace-notice" role="alert">
          <Settings2 :size="16" /><span>{{ configError }}</span><RouterLink to="/settings" class="underline">配置模型 <ArrowRight :size="12" /></RouterLink>
        </div>
      </div>

      <p v-if="showError" class="workspace-error" role="alert">这看起来不是 B 站链接，请粘贴 bilibili.com 或 b23.tv 链接。</p>
      <p v-else-if="submitted" class="workspace-error" role="alert">{{ submitted }}</p>

      <!-- 视频预览卡 -->
      <div v-if="isBilibili" class="glass-panel mt-4 flex items-center gap-4 rounded-[14px] p-3">
        <span class="workspace-video-icon"><Link2 :size="23" /></span>
        <div class="min-w-0">
          <p class="truncate text-[14px] font-medium">已识别 B 站视频 · {{ videoId }}</p>
          <p class="mt-1 text-[11.5px] text-faint">解析后显示封面、标题、UP 主与时长</p>
        </div>
        <button class="ml-auto text-[12px] text-muted hover:text-ink" @click="url = ''">移除</button>
      </div>

      <!-- 合集 / 多 P 识别 -->
      <div v-if="collectionLoading" class="glass-panel mt-4 rounded-[14px] px-4 py-3 text-[12px] text-muted">
        正在识别分 P / 合集…
      </div>
      <div v-else-if="collectionError" class="glass-panel mt-4 rounded-[14px] px-4 py-3 text-[12px] text-accent">
        {{ collectionError }}
      </div>
      <div v-else-if="collection && collection.total > 1" class="glass-card mt-4 rounded-[14px] p-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <p class="text-[11px] uppercase tracking-[.12em] text-accent">
              {{ collection.kind === 'pages' ? '多 P 视频' : collection.kind === 'season' ? '视频合集' : 'UP 主系列' }}
            </p>
            <h3 class="mt-1 text-[15px] font-medium">识别到 {{ collection.total }} P · {{ collection.title }}</h3>
            <p class="mt-1 text-[11.5px] text-faint">已生成 {{ collection.items.filter(item => item.generated).length }} P，可只选未生成。</p>
          </div>
          <span class="rounded-full bg-accent-soft px-2.5 py-1 text-[11px] text-accent">{{ selectedCollectionIds.length }} 已选</span>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-2">
          <button class="rounded-md border border-line px-2.5 py-1 text-[11.5px] text-muted hover:bg-surface-2" @click="selectAllCollection">全选</button>
          <button class="rounded-md border border-line px-2.5 py-1 text-[11.5px] text-muted hover:bg-surface-2" @click="selectUngenerated">只选未生成</button>
          <button class="rounded-md border border-line px-2.5 py-1 text-[11.5px] text-muted hover:bg-surface-2" @click="clearCollectionSelection">清空</button>
          <span class="ml-1 text-[11px] text-faint">范围</span>
          <input v-model.number="rangeStart" type="number" min="1" :max="collection.total" class="h-7 w-14 rounded border border-line bg-surface px-1.5 text-[11px]" />
          <span class="text-[11px] text-faint">–</span>
          <input v-model.number="rangeEnd" type="number" min="1" :max="collection.total" class="h-7 w-14 rounded border border-line bg-surface px-1.5 text-[11px]" />
          <button class="rounded-md border border-line px-2.5 py-1 text-[11.5px] text-muted hover:bg-surface-2" @click="applyCollectionRange">选范围</button>
        </div>

        <div class="mt-3 max-h-[210px] overflow-y-auto rounded-[9px] border border-line bg-surface/40">
          <label
            v-for="item in collection.items"
            :key="item.video_id"
            class="flex cursor-pointer items-center gap-2.5 border-b border-line-soft px-3 py-2 last:border-0"
            :class="item.generated ? 'opacity-55' : 'hover:bg-surface-2'"
          >
            <input
              type="checkbox"
              :checked="selectedCollectionIds.includes(item.video_id)"
              :disabled="item.generated"
              class="accent-[var(--color-accent)]"
              @change="toggleCollectionItem(item.video_id)"
            />
            <span class="w-5 text-[11px] text-faint">{{ item.page || '·' }}</span>
            <span class="min-w-0 flex-1 truncate text-[12px]">{{ item.title }}</span>
            <span class="shrink-0 text-[10.5px] text-faint">{{ Math.floor(item.duration / 60) }}:{{ String(item.duration % 60).padStart(2, '0') }}</span>
            <span v-if="item.generated" class="shrink-0 text-[10px] text-success">已生成</span>
          </label>
        </div>

        <div class="mt-3 flex items-center gap-2">
          <select v-model.number="batchConcurrency" class="h-8 w-[88px] shrink-0 rounded-[7px] border border-line bg-surface px-2 text-[11.5px] text-muted outline-none">
            <option :value="1">并发 1</option>
            <option :value="2">并发 2</option>
            <option :value="3">并发 3</option>
          </select>
          <select v-model="batchGroupId" class="h-8 min-w-0 flex-1 rounded-[7px] border border-line bg-surface px-2 text-[11.5px] text-muted outline-none">
            <option value="">自动创建分组「{{ collection.title.slice(0, 20) }}」</option>
            <option v-for="group in library.sortedGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
          </select>
          <button
            class="h-8 rounded-[8px] bg-accent px-3 text-[12px] text-white disabled:opacity-40"
            :disabled="batchBusy || !selectedCollectionIds.length"
            @click="generateCollection"
          >
            {{ batchBusy ? batchProgress || '提交中…' : `批量生成 ${selectedCollectionIds.length} P` }}
          </button>
        </div>
        <p v-if="batchProgress" class="mt-2 text-[11px] text-accent">{{ batchProgress }}</p>
      </div>

      <!-- 最近笔记 -->
      <section class="glass-panel study-recent mt-7 rounded-[16px] p-5">
        <div class="workspace-section-heading">
          <div><h2>我的学习笔记</h2><p>知识有归处，温习有方向。</p></div>
          <div class="flex items-center gap-4">
            <button class="text-[12px] text-accent hover:underline" @click="newGroupOpen = true">＋ 新建分组</button>
            <RouterLink to="/library" class="text-[12px] text-muted hover:text-ink">查看全部 →</RouterLink>
          </div>
        </div>

        <div class="workspace-library-toolbar">
          <div class="workspace-filters" aria-label="笔记状态筛选">
            <button v-for="filter in noteFilters" :key="filter.id" :aria-pressed="noteFilter === filter.id" :class="{ selected: noteFilter === filter.id }" @click="noteFilter = filter.id">{{ filter.label }}<span>{{ filter.count }}</span></button>
          </div>
          <label class="workspace-note-search"><Search :size="14" /><input v-model="noteQuery" placeholder="查找笔记…" aria-label="筛选笔记标题或作者" /><button v-if="noteQuery" aria-label="清空笔记搜索" @click="noteQuery = ''"><X :size="12" /></button></label>
        </div>

        <p v-if="library.error" class="workspace-error" role="alert">笔记暂时无法加载。{{ library.error }} <button class="underline" @click="library.load()">重试</button></p>
        <div v-else-if="!library.loaded" class="workspace-note-loading" role="status"><LoaderCircle :size="18" class="workspace-spinner" /> 正在整理你的学习记录…</div>

        <div v-if="newGroupOpen" class="glass-panel mt-3 flex items-center gap-2 rounded-lg p-2">
          <Folder :size="15" class="text-accent" />
          <input
            v-model="newGroupName"
            autofocus
            class="h-8 flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint"
            placeholder="分组名，例如：考研数学"
            @keydown.enter="createGroup"
            @keydown.esc="newGroupOpen = false"
          />
          <button class="rounded-md bg-accent px-3 py-1.5 text-[12px] text-white" @click="createGroup">创建</button>
          <button class="px-2 text-[12px] text-muted" @click="newGroupOpen = false">取消</button>
        </div>
        <p v-if="newGroupError" class="mt-1 text-[11.5px] text-accent">{{ newGroupError }}</p>

        <div v-if="library.loaded && !library.notes.length && !library.error" class="study-empty workspace-empty">
          <span class="workspace-empty-icon"><BookOpen :size="30" :stroke-width="1.3" /></span>
          <h3>你的知识库，等第一颗种子</h3>
          <p>导入一节感兴趣的课程，重点、脉络和灵感都会留在这里。</p>
          <button @click="urlInput?.focus(); urlInput?.scrollIntoView({ behavior: 'smooth', block: 'center' })">开始第一节课 <ArrowRight :size="14" /></button>
        </div>
        <div v-else-if="library.loaded && library.notes.length && !filteredNotes.length" class="workspace-no-results"><Search :size="24" /><p>没有符合条件的笔记</p><button @click="noteQuery = ''; noteFilter = 'all'">清除筛选</button></div>

        <div v-for="group in visibleGroups" :key="group.id" class="workspace-note-group mt-2">
          <div class="flex items-center gap-2 py-3">
            <Folder :size="14" class="text-muted" />
            <input
              v-if="editingGroupId === group.id"
              v-model="editingGroupName"
              autofocus
              class="h-7 min-w-0 flex-1 rounded border border-accent bg-surface px-2 text-[13px] outline-none"
              aria-label="分组名称"
              @click.stop
              @keydown.enter.stop="commitRename"
              @keydown.esc.stop="cancelRename"
              @blur="commitRename"
            />
            <button v-else class="min-w-0 flex-1 truncate text-left text-[13px] font-medium" :title="group.name" :aria-expanded="!library.collapsed[group.id]" @click="library.toggleGroup(group.id)">{{ group.name }}</button>
            <span class="shrink-0 text-[11px] text-faint">{{ library.notesOfGroup(group.id).length }} 篇</span>
            <component :is="library.collapsed[group.id] ? ChevronRight : ChevronDown" :size="14" class="shrink-0 text-faint" />
            <button class="ml-auto shrink-0 text-faint hover:text-ink" title="重命名分组" @click.stop="startRename(group)">
              <Pencil :size="13" />
            </button>
            <button class="ml-1 flex h-6 w-6 items-center justify-center rounded border border-line text-faint hover:border-accent hover:text-accent" title="下载本组全部 Markdown" @click.stop="downloadGroup(group.id, group.name)">
              <FileDown :size="12" />
            </button>
          </div>

          <ul v-if="!library.collapsed[group.id]">
            <li
              v-for="note in filteredNotes.filter(item => item.groupId === group.id)"
              :key="note.id"
              class="flex cursor-pointer items-center gap-4 border-b border-line-soft py-3 pl-5 hover:bg-surface-2"
              @click="openNote(note)"
            >
              <span class="w-[74px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
              <button class="min-w-0 flex-1 text-left" @click.stop="openNote(note)">
                <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
                <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
              </button>
              <select
                :value="note.groupId ?? ''"
                class="ml-auto h-7 w-[96px] shrink-0 rounded border border-line bg-surface-2 px-1.5 text-[11px] text-muted outline-none"
                title="移动到分组"
                @click.stop
                @change="moveNote(note, $event)"
              >
                <option value="">未分组</option>
                <option v-for="g in library.sortedGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
              <span
                class="flex shrink-0 items-center gap-1.5 text-[11.5px]"
                :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
              >
                <span class="h-[5px] w-[5px] rounded-full" :class="note.status === 'done' ? 'bg-success' : note.status === 'running' ? 'bg-accent' : note.status === 'failed' ? 'bg-red-500' : 'bg-faint'" />
                {{ statusLabel(note.status) }}
              </span>
            </li>
          </ul>
        </div>

        <!-- 未分组 -->
        <div v-if="filteredUngrouped.length" class="workspace-note-group mt-2">
          <button class="flex w-full items-center gap-2 py-3 text-left" @click="library.toggleGroup('ungrouped')">
            <Folder :size="14" class="text-muted" />
            <span class="text-[13px] font-medium">未分组</span>
            <span class="text-[11px] text-faint">{{ library.ungrouped.length }} 篇</span>
            <component :is="library.collapsed.ungrouped ? ChevronRight : ChevronDown" :size="14" class="ml-auto text-faint" />
          </button>
          <ul v-if="!library.collapsed.ungrouped">
            <li
              v-for="note in filteredUngrouped"
              :key="note.id"
              class="flex cursor-pointer items-center gap-4 border-b border-line-soft py-3 pl-5 hover:bg-surface-2"
              @click="openNote(note)"
            >
              <span class="w-[74px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
              <button class="min-w-0 flex-1 text-left" @click.stop="openNote(note)">
                <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
                <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
              </button>
              <select
                :value="note.groupId ?? ''"
                class="ml-auto h-7 w-[96px] shrink-0 rounded border border-line bg-surface-2 px-1.5 text-[11px] text-muted outline-none"
                title="移动到分组"
                @click.stop
                @change="moveNote(note, $event)"
              >
                <option value="">未分组</option>
                <option v-for="g in library.sortedGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
              <span
                class="flex shrink-0 items-center gap-1.5 text-[11.5px]"
                :class="note.status === 'done' ? 'text-success' : note.status === 'running' ? 'text-accent' : note.status === 'failed' ? 'text-red-500' : 'text-faint'"
              >
                <span class="h-[5px] w-[5px] rounded-full" :class="note.status === 'done' ? 'bg-success' : note.status === 'running' ? 'bg-accent' : note.status === 'failed' ? 'bg-red-500' : 'bg-faint'" />
                {{ statusLabel(note.status) }}
              </span>
            </li>
          </ul>
        </div>
      </section>
      </div>
      <aside class="study-aside">
        <section class="workspace-setup">
          <div class="aside-title"><span>学习准备</span><Settings2 :size="16" /></div>
          <RouterLink to="/settings" class="workspace-setup-row"><span class="setup-indicator" :class="{ ready: !!selectedModel }"><Check v-if="selectedModel" :size="12" /><Settings2 v-else :size="12" /></span><div><b>笔记生成模型</b><p>{{ configLoading ? '正在读取配置…' : selectedModel || '配置模型后即可生成笔记' }}</p></div><ChevronRight :size="14" /></RouterLink>
          <RouterLink to="/settings?tab=transcriber" class="workspace-setup-row"><span class="setup-indicator" :class="{ ready: transcriberReady }"><Check v-if="transcriberReady" :size="12" /><Settings2 v-else :size="12" /></span><div><b>音频转写引擎</b><p>{{ transcriberLabel }}</p><small v-if="transcriberReady === false">本地模型尚未下载，去设置下载</small></div><ChevronRight :size="14" /></RouterLink>
          <p class="workspace-setup-hint">模型与引擎可随时在设置中调整。</p>
        </section>
        <section class="study-guide">
          <div class="aside-title"><span>学习可以很简单</span><Sparkles :size="16" /></div>
          <ol><li><span>01</span><div><b>收藏一节好课</b><p>粘贴链接，单集或合集都可以</p></div></li><li><span>02</span><div><b>梳理知识脉络</b><p>提炼重点，生成笔记与思维导图</p></div></li><li><span>03</span><div><b>把知识变成自己的</b><p>回看笔记，带着问题继续探索</p></div></li></ol>
        </section>
        <RouterLink to="/tasks" class="workspace-task-link"><span><Clock3 :size="18" /><b>查看生成任务</b></span><p>{{ activeCount ? `有 ${activeCount} 个任务正在等待或生成` : '在这里查看笔记生成进度' }}</p><ArrowUpRight :size="16" /></RouterLink>
      </aside>
      </div>
      <footer class="study-footer"><Leaf :size="13" /> 老哔拾课 · 把知识拾起，把成长留下</footer>
    </div>
  </div>
</template>
