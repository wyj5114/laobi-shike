<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Cpu, KeyRound, Palette, Info, Boxes, Plus, X, Check } from 'lucide-vue-next'
import { api, type ApiProvider, type ApiModel } from '@/services/api'
import { THEMES, applyTheme, getStoredTheme, type ThemeId } from '@/design/themes'
import TranscriberSettings from '@/components/settings/TranscriberSettings.vue'

const route = useRoute()
const active = ref(String(route.query.tab || 'model'))
const nav = [
  { key: 'model', label: '模型服务', icon: Boxes },
  { key: 'transcriber', label: '转写引擎', icon: Cpu },
  { key: 'bilibili', label: 'B 站设置', icon: KeyRound },
  { key: 'appearance', label: '外观', icon: Palette },
  { key: 'about', label: '关于', icon: Info },
]

const providers = ref<ApiProvider[]>([])
const selectedId = ref('')
const selected = computed(() => providers.value.find(p => p.id === selectedId.value) ?? null)
const form = reactive({ name: '', base_url: '', api_key: '' })
const enabledModels = ref<ApiModel[]>([])
const upstreamModels = ref<ApiModel[]>([])
const modelSearch = ref('')
const pickedModel = ref('')
const addOpen = ref(false)
const newProvider = reactive({ name: '', base_url: '', api_key: '' })
const message = ref('')
const busy = ref(false)

const filteredModels = computed(() => {
  const keyword = modelSearch.value.trim().toLowerCase()
  if (!keyword) return upstreamModels.value
  return upstreamModels.value.filter(item => String(item.id).toLowerCase().includes(keyword))
})

const cookie = ref('')
const fontSize = ref('16.5')
const activeTheme = ref<ThemeId>(getStoredTheme())

function chooseTheme(id: ThemeId) {
  activeTheme.value = id
  applyTheme(id)
}

onMounted(loadProviders)

function modelId(model: ApiModel): string {
  return String(model.model_name ?? model.id)
}

async function loadProviders() {
  try {
    const list = await api.listProviders()
    providers.value = list.sort(
      (a, b) => Number(Boolean(b.api_key)) - Number(Boolean(a.api_key)) || a.name.localeCompare(b.name),
    )
    const keep = providers.value.find(p => p.id === selectedId.value)
    await selectProvider(keep ?? providers.value[0])
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function selectProvider(provider?: ApiProvider) {
  if (!provider) return
  selectedId.value = provider.id
  form.name = provider.name
  form.base_url = provider.base_url
  form.api_key = provider.api_key
  pickedModel.value = ''
  modelSearch.value = ''
  await loadModels()
}

async function loadModels() {
  enabledModels.value = []
  upstreamModels.value = []
  if (!selected.value?.api_key) return
  try {
    const [saved, remote] = await Promise.all([
      api.listEnabledModels(selected.value.id),
      api.listModels(selected.value.id).catch(() => ({ models: [] as ApiModel[] })),
    ])
    enabledModels.value = saved
    upstreamModels.value = remote.models ?? []
    pickedModel.value = upstreamModels.value[0] ? String(upstreamModels.value[0].id) : ''
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function saveProvider() {
  if (!selected.value) return
  busy.value = true
  try {
    await api.updateProvider({
      id: selected.value.id,
      name: form.name,
      base_url: form.base_url,
      api_key: form.api_key,
    })
    selected.value.name = form.name
    selected.value.base_url = form.base_url
    selected.value.api_key = form.api_key
    await loadModels()
    message.value = `${form.name} 已保存`
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  } finally {
    busy.value = false
  }
}

async function testProvider() {
  if (!selected.value) return
  try {
    await api.connectTest(selected.value.id, enabledModels.value[0] ? modelId(enabledModels.value[0]) : undefined)
    message.value = `${selected.value.name} 连接成功`
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function toggleProvider(provider: ApiProvider) {
  try {
    const enabled = provider.enabled ? 0 : 1
    await api.updateProvider({ id: provider.id, enabled })
    provider.enabled = enabled
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function addProvider() {
  if (!newProvider.name.trim() || !newProvider.base_url.trim()) {
    message.value = '供应商名称和 Base URL 必填'
    return
  }
  try {
    await api.addProvider({
      name: newProvider.name.trim(),
      base_url: newProvider.base_url.trim(),
      api_key: newProvider.api_key,
      logo: newProvider.name.slice(0, 1).toUpperCase(),
      type: 'custom',
    })
    addOpen.value = false
    const name = newProvider.name.trim()
    newProvider.name = ''
    newProvider.base_url = ''
    newProvider.api_key = ''
    await loadProviders()
    const created = providers.value.find(p => p.name === name)
    if (created) await selectProvider(created)
    message.value = '供应商已添加'
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function addModel() {
  if (!selected.value || !pickedModel.value) return
  try {
    await api.addModel(selected.value.id, pickedModel.value)
    await loadModels()
    message.value = `已添加模型 ${pickedModel.value}`
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function removeModel(model: ApiModel) {
  if (!window.confirm(`确定移除模型 ${modelId(model)} 吗？`)) return
  try {
    await api.deleteModel(model.id)
    await loadModels()
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
  }
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto w-[980px] pb-24 pt-10">
      <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Settings</p>
      <h1 class="mt-2 text-[30px] font-semibold tracking-[-0.025em]">设置</h1>

      <div class="mt-8 flex gap-10">
        <aside class="w-[170px] shrink-0">
          <button
            v-for="item in nav"
            :key="item.key"
            class="mb-1 flex w-full items-center gap-2.5 rounded-[9px] px-3 py-2.5 text-left text-[13px]"
            :class="active === item.key ? 'bg-accent-soft font-medium text-accent' : 'text-muted hover:bg-surface-2 hover:text-ink'"
            @click="active = item.key"
          >
            <component :is="item.icon" :size="15" :stroke-width="1.7" />
            {{ item.label }}
          </button>
        </aside>

        <section class="min-w-0 flex-1">
          <!-- 模型服务：左供应商列表 + 右详情 -->
          <div v-if="active === 'model'" class="flex gap-5">
            <aside class="w-[220px] shrink-0">
              <button
                class="flex h-9 w-full items-center justify-center gap-1.5 rounded-[9px] bg-accent text-[12.5px] text-white"
                @click="addOpen = !addOpen"
              >
                <Plus :size="14" /> 添加供应商
              </button>

              <div v-if="addOpen" class="glass-panel mt-2 space-y-2 rounded-[10px] p-3">
                <input v-model="newProvider.name" class="h-8 w-full rounded-[7px] border border-line px-2 text-[12px] outline-none focus:border-accent" placeholder="名称，如 WB2API" />
                <input v-model="newProvider.base_url" class="h-8 w-full rounded-[7px] border border-line px-2 text-[12px] outline-none focus:border-accent" placeholder="Base URL" />
                <input v-model="newProvider.api_key" class="h-8 w-full rounded-[7px] border border-line px-2 font-mono text-[12px] outline-none focus:border-accent" placeholder="API Key" type="password" />
                <div class="flex gap-2">
                  <button class="h-8 flex-1 rounded-[7px] bg-accent text-[12px] text-white" @click="addProvider">创建</button>
                  <button class="h-8 rounded-[7px] border border-line px-2 text-[12px] text-muted" @click="addOpen = false">取消</button>
                </div>
              </div>

              <div class="mt-4 mb-2 text-[11px] uppercase tracking-[.12em] text-faint">供应商</div>
              <button
                v-for="p in providers"
                :key="p.id"
                class="mb-1 flex w-full items-center gap-2.5 rounded-[9px] px-2.5 py-2.5 text-left"
                :class="selectedId === p.id ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-surface-2 hover:text-ink'"
                @click="selectProvider(p)"
              >
                <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] bg-surface text-[12px] font-semibold text-accent">{{ p.name.slice(0, 1) }}</span>
                <span class="min-w-0 flex-1 truncate text-[12.5px]">{{ p.name }}</span>
                <span class="h-1.5 w-1.5 rounded-full" :class="p.api_key ? 'bg-success' : 'bg-line'" />
              </button>
            </aside>

            <section v-if="selected" class="glass-card min-w-0 flex-1 rounded-[14px] p-5">
              <div class="flex items-start justify-between">
                <div>
                  <h2 class="text-[17px] font-semibold">{{ selected.name }}</h2>
                  <p class="mt-1 text-[11.5px] text-faint">{{ selected.base_url }}</p>
                </div>
                <button
                  class="rounded-full px-3 py-1 text-[11.5px]"
                  :class="selected.enabled ? 'bg-emerald-50 text-success' : 'bg-surface-2 text-faint'"
                  @click="toggleProvider(selected)"
                >
                  {{ selected.enabled ? '已启用' : '已停用' }}
                </button>
              </div>

              <div class="mt-5 grid grid-cols-2 gap-3">
                <label class="text-[12px] text-muted">
                  名称
                  <input v-model="form.name" class="mt-1 h-9 w-full rounded-[8px] border border-line bg-surface-2 px-3 text-[12.5px] outline-none focus:border-accent" />
                </label>
                <label class="text-[12px] text-muted">
                  Base URL
                  <input v-model="form.base_url" class="mt-1 h-9 w-full rounded-[8px] border border-line bg-surface-2 px-3 font-mono text-[12px] outline-none focus:border-accent" />
                </label>
              </div>
              <label class="mt-3 block text-[12px] text-muted">
                API Key
                <input v-model="form.api_key" class="mt-1 h-9 w-full rounded-[8px] border border-line bg-surface-2 px-3 font-mono text-[12px] outline-none focus:border-accent" type="password" placeholder="sk-..." />
              </label>

              <div class="mt-4 flex gap-2">
                <button class="h-9 rounded-[8px] bg-accent px-4 text-[12.5px] text-white disabled:opacity-50" :disabled="busy" @click="saveProvider">{{ busy ? '保存中…' : '保存' }}</button>
                <button class="h-9 rounded-[8px] border border-line px-4 text-[12.5px] text-muted hover:bg-surface-2" @click="testProvider">测试连接</button>
              </div>

              <div class="mt-6 border-t border-line-soft pt-4">
                <div class="flex items-center justify-between">
                  <h3 class="text-[13.5px] font-medium">模型</h3>
                  <span class="text-[11px] text-faint">已启用 {{ enabledModels.length }} 个</span>
                </div>

                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="model in enabledModels"
                    :key="String(model.id)"
                    class="glass-chip flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] text-ink-2"
                  >
                    {{ modelId(model) }}
                    <button class="text-faint hover:text-red-500" @click="removeModel(model)"><X :size="11" /></button>
                  </span>
                  <span v-if="!enabledModels.length" class="text-[12px] text-faint">还没有启用模型，先从下方添加。</span>
                </div>

                <div class="mt-4 flex items-center gap-2">
                  <input v-model="modelSearch" class="h-9 w-[180px] rounded-[8px] border border-line bg-surface-2 px-3 text-[12px] outline-none focus:border-accent" placeholder="搜索上游模型" />
                  <select v-model="pickedModel" class="h-9 min-w-0 flex-1 rounded-[8px] border border-line bg-surface-2 px-2 text-[12px] outline-none">
                    <option v-for="model in filteredModels" :key="String(model.id)" :value="String(model.id)">{{ String(model.id) }}</option>
                  </select>
                  <button class="h-9 rounded-[8px] border border-line px-3 text-[12px] text-muted hover:bg-surface-2" @click="addModel">添加模型</button>
                </div>
              </div>

              <p v-if="message" class="mt-3 text-[11.5px] text-muted">{{ message }}</p>
            </section>
          </div>

          <!-- 转写引擎 -->
          <TranscriberSettings v-else-if="active === 'transcriber'" @open-models="active = 'model'" />

          <!-- B 站设置 -->
          <div v-else-if="active === 'bilibili'" class="space-y-3">
            <h2 class="text-[16px] font-semibold">B 站 Cookie</h2>
            <p class="text-[12px] text-muted">部分视频需要登录态才能获取字幕或高清音频。仅保存在本机。</p>
            <textarea
              v-model="cookie"
              rows="6"
              class="w-full rounded-[10px] border border-line bg-surface p-3 font-mono text-[12px] outline-none focus:border-accent"
              placeholder="SESSDATA=...; bili_jct=...;"
            />
            <div class="flex gap-2">
              <button class="h-8 rounded-[8px] bg-accent px-3 text-[12.5px] text-white">保存</button>
              <button class="h-8 rounded-[8px] border border-line px-3 text-[12.5px] text-muted">测试连接</button>
            </div>
          </div>

          <!-- 外观 -->
          <div v-else-if="active === 'appearance'" class="space-y-5">
            <h2 class="text-[16px] font-semibold">外观</h2>
            <div>
              <p class="mb-3 text-[12.5px] text-muted">主题</p>
              <div class="grid grid-cols-2 gap-3">
                <button
                  v-for="theme in THEMES"
                  :key="theme.id"
                  class="relative rounded-[12px] border p-3 text-left transition-colors"
                  :class="activeTheme === theme.id ? 'border-accent bg-accent-soft/60' : 'border-line bg-surface/50 hover:border-accent/40'"
                  @click="chooseTheme(theme.id)"
                >
                  <div class="flex gap-1.5">
                    <span
                      v-for="color in theme.colors"
                      :key="color"
                      class="h-5 w-5 rounded-full border border-ink/10 shadow-sm"
                      :style="{ background: color }"
                    />
                  </div>
                  <p class="mt-3 text-[13px] font-medium">{{ theme.name }}</p>
                  <p class="mt-0.5 text-[11.5px] text-faint">{{ theme.subtitle }}</p>
                  <span
                    v-if="activeTheme === theme.id"
                    class="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-white"
                  >
                    <Check :size="12" />
                  </span>
                </button>
              </div>
            </div>
            <div>
              <p class="mb-2 text-[12.5px] text-muted">正文字号</p>
              <div class="flex gap-2">
                <button
                  v-for="size in ['15', '16.5', '18']"
                  :key="size"
                  class="rounded-[8px] border px-4 py-2 text-[12.5px]"
                  :class="fontSize === size ? 'border-accent bg-accent-soft text-accent' : 'border-line text-muted'"
                  @click="fontSize = size"
                >
                  {{ size }}px
                </button>
              </div>
            </div>
          </div>

          <!-- 关于 -->
          <div v-else class="space-y-2">
            <h2 class="text-[16px] font-semibold">关于</h2>
            <p class="text-[12.5px] text-muted">哔站拾课 · 0.1.0</p>
            <p class="text-[12.5px] text-faint">把 B 站课程，变成你的笔记。</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
