<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, ChevronRight, FileDown, Folder, Link2, Pencil } from 'lucide-vue-next'
import { useLibraryStore, type NoteSummary } from '@/stores/library'
import { api, type ApiCollection, type ApiModel, type ApiProvider } from '@/services/api'

const router = useRouter()
const library = useLibraryStore()

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
  if (collectionTimer) window.clearTimeout(collectionTimer)
  collection.value = null
  selectedCollectionIds.value = []
  collectionError.value = ''
  if (!/(bilibili\.com\/video\/|b23\.tv\/)/i.test(value)) return
  collectionTimer = window.setTimeout(loadCollection, 700)
})

onMounted(async () => {
  await library.load()
  await loadModelConfig()
  if (isBilibili.value) void loadCollection()
  refreshTimer = window.setInterval(() => library.load(), 5000)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
  if (collectionTimer) window.clearTimeout(collectionTimer)
})

async function loadModelConfig() {
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
  }
}
const showError = computed(() => url.value.trim().length > 0 && !isBilibili.value)

const videoId = computed(() => {
  const match = url.value.match(/(BV[a-zA-Z0-9]+)/)
  return match?.[1] ?? 'BV1xx411c7mD'
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
  collectionLoading.value = true
  collectionError.value = ''
  try {
    const data = await api.getCollection(url.value)
    collection.value = data
    rangeStart.value = 1
    rangeEnd.value = data.total
  } catch (error) {
    collectionError.value = error instanceof Error ? error.message : String(error)
  } finally {
    collectionLoading.value = false
  }
}

function toggleCollectionItem(id: string) {
  selectedCollectionIds.value = selectedCollectionIds.value.includes(id)
    ? selectedCollectionIds.value.filter(item => item !== id)
    : [...selectedCollectionIds.value, id]
}

function selectAllCollection() {
  if (!collection.value) return
  selectedCollectionIds.value = collection.value.items.map(item => item.video_id)
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
  if (!isBilibili.value) return
  if (!selectedProvider.value || !selectedModel.value) {
    submitted.value = configError.value || '请先在设置中配置模型 API Key'
    return
  }
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
  <div class="h-full overflow-y-auto">
    <div class="mx-auto w-[760px] pb-24 pt-20">
      <p class="mb-4 text-[11.5px] uppercase tracking-[.16em] text-accent">哔站拾课 · 课程笔记</p>
      <h1 class="text-[42px] font-semibold leading-[1.2] tracking-[-0.03em]">今天想学点什么？</h1>
      <p class="mt-3 text-[14.5px] text-muted">粘贴 B 站视频链接，剩下的交给哔站拾课。</p>

      <!-- 输入台 -->
      <div class="glass-card glass-card-hover mt-9 rounded-[16px] p-2.5">
        <div class="flex items-center gap-3 px-3 py-1.5">
          <Link2 :size="18" :stroke-width="1.7" class="shrink-0 text-faint" />
          <input
            v-model="url"
            class="h-10 min-w-0 flex-1 bg-transparent text-[15.5px] text-ink outline-none placeholder:text-faint"
            placeholder="粘贴 B 站视频链接，回车开始…"
            @keydown.enter="submit"
          />
          <button
            class="h-10 shrink-0 rounded-[9px] px-5 text-[13.5px] tracking-[.02em] transition-colors"
            :class="isBilibili ? 'bg-accent text-white hover:bg-[#1d4ed8]' : 'cursor-not-allowed bg-surface-2 text-faint'"
            @click="submit"
          >
            生成笔记
          </button>
        </div>

        <div class="mt-1 flex items-center gap-2 border-t border-line-soft px-3 pb-1.5 pt-2.5">
          <label class="glass-chip flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-muted">
            模型 ·
            <select v-model="selectedModel" class="max-w-[190px] bg-transparent text-[12px] text-ink outline-none">
              <option v-if="!availableModels.length" value="">未配置</option>
              <option v-for="item in availableModels" :key="String(item.id)" :value="String(item.model_name ?? item.id)">
                {{ item.model_name ?? item.id }}
              </option>
            </select>
          </label>
          <label class="glass-chip flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-muted">
            风格 ·
            <select v-model="selectedStyle" class="bg-transparent text-[12px] text-ink outline-none">
              <option v-for="item in styles" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <span class="glass-chip rounded-md px-2 py-1 text-[12px] text-muted">格式 · {{ formats.join(' + ') }}</span>
        </div>

        <div v-if="configError" class="border-t border-line-soft px-3 py-2 text-[11.5px] text-accent">
          {{ configError }} · <RouterLink to="/settings" class="underline">去设置</RouterLink>
        </div>
      </div>

      <p v-if="showError" class="mt-2 text-[12.5px] text-accent">这看起来不是 B 站链接，请粘贴 bilibili.com 或 b23.tv 链接。</p>
      <p v-else-if="submitted" class="mt-2 text-[12.5px] text-success">{{ submitted }}</p>

      <!-- 视频预览卡 -->
      <div v-if="isBilibili" class="glass-panel mt-4 flex items-center gap-4 rounded-[14px] p-3">
        <div class="h-[62px] w-[110px] shrink-0 rounded-lg bg-[linear-gradient(135deg,var(--color-rail)_0%,var(--color-rail-2)_55%,var(--color-accent)_100%)]" />
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
      <section class="glass-panel mt-12 rounded-[16px] p-5">
        <div class="flex items-baseline justify-between border-b border-line pb-3">
          <h2 class="text-[17px] font-semibold tracking-[-0.01em]">最近笔记</h2>
          <div class="flex items-center gap-4">
            <button class="text-[12px] text-accent hover:underline" @click="newGroupOpen = true">＋ 新建分组</button>
            <RouterLink to="/library" class="text-[12px] text-muted hover:text-ink">查看全部 →</RouterLink>
          </div>
        </div>

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

        <div v-for="group in library.sortedGroups" :key="group.id" class="mt-2">
          <div class="flex cursor-pointer items-center gap-2 py-3" @click="library.toggleGroup(group.id)">
            <Folder :size="14" class="text-muted" />
            <input
              v-if="editingGroupId === group.id"
              v-model="editingGroupName"
              autofocus
              class="h-7 w-[180px] rounded border border-accent bg-surface px-2 text-[13px] outline-none"
              @click.stop
              @keydown.enter.stop="commitRename"
              @keydown.esc.stop="cancelRename"
              @blur="commitRename"
            />
            <span v-else class="text-[13px] font-medium">{{ group.name }}</span>
            <span class="text-[11px] text-faint">{{ library.notesOfGroup(group.id).length }} 篇</span>
            <component :is="library.collapsed[group.id] ? ChevronRight : ChevronDown" :size="14" class="text-faint" />
            <button class="ml-auto text-faint hover:text-ink" title="重命名分组" @click.stop="startRename(group)">
              <Pencil :size="13" />
            </button>
            <button class="ml-1 flex h-6 w-6 items-center justify-center rounded border border-line text-faint hover:border-accent hover:text-accent" title="下载本组全部 Markdown" @click.stop="downloadGroup(group.id, group.name)">
              <FileDown :size="12" />
            </button>
          </div>

          <ul v-if="!library.collapsed[group.id]">
            <li
              v-for="note in library.notesOfGroup(group.id)"
              :key="note.id"
              class="flex cursor-pointer items-center gap-4 border-b border-line-soft py-3 pl-5 hover:bg-surface-2"
              @click="openNote(note)"
            >
              <span class="w-[74px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
              <div class="min-w-0">
                <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
                <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
              </div>
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
        <div v-if="library.ungrouped.length" class="mt-2">
          <button class="flex w-full items-center gap-2 py-3 text-left" @click="library.toggleGroup('ungrouped')">
            <Folder :size="14" class="text-muted" />
            <span class="text-[13px] font-medium">未分组</span>
            <span class="text-[11px] text-faint">{{ library.ungrouped.length }} 篇</span>
            <component :is="library.collapsed.ungrouped ? ChevronRight : ChevronDown" :size="14" class="ml-auto text-faint" />
          </button>
          <ul v-if="!library.collapsed.ungrouped">
            <li
              v-for="note in library.ungrouped"
              :key="note.id"
              class="flex cursor-pointer items-center gap-4 border-b border-line-soft py-3 pl-5 hover:bg-surface-2"
              @click="openNote(note)"
            >
              <span class="w-[74px] shrink-0 text-[11.5px] text-faint">{{ note.createdAt }}</span>
              <div class="min-w-0">
                <p class="truncate text-[14px] font-medium">{{ note.title }}</p>
                <p class="mt-1 text-[11.5px] text-faint">{{ note.author }} · {{ note.duration }} · {{ note.style }}</p>
              </div>
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
  </div>
</template>
