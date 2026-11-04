<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, type ApiTranscriberConfig, type ApiTranscriberModelStatus } from '@/services/api'

defineEmits<{ 'open-models': [] }>()

const config = ref<ApiTranscriberConfig | null>(null)
const engine = ref('')
const model = ref('')
const savedEngine = ref('')
const savedModel = ref('')
const statuses = ref<{ whisper: ApiTranscriberModelStatus[]; mlx_whisper: ApiTranscriberModelStatus[] }>({ whisper: [], mlx_whisper: [] })
const loading = ref(true)
const saving = ref(false)
const downloading = ref(false)
const message = ref('')
const error = ref('')
let timer: number | undefined
let disposed = false
const local = computed(() => ['fast-whisper', 'mlx-whisper'].includes(engine.value))
const currentStatus = computed(() => (engine.value === 'mlx-whisper' ? statuses.value.mlx_whisper : statuses.value.whisper).find(row => row.model_size === model.value))
const hasChanges = computed(() => engine.value !== savedEngine.value || model.value !== savedModel.value)

async function refreshStatus() {
  statuses.value = await api.getTranscriberModelsStatus()
}

async function retry() {
  if (!config.value) return load()
  error.value = ''
  try {
    await refreshStatus()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  }
}

async function pollStatus() {
  try {
    await refreshStatus()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    if (!disposed) timer = window.setTimeout(pollStatus, 3000)
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.getTranscriberConfig()
    config.value = result
    engine.value = savedEngine.value = result.transcriber_type
    model.value = savedModel.value = result.whisper_model_size
    await refreshStatus()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  message.value = error.value = ''
  try {
    const saved = await api.saveTranscriberConfig({ transcriber_type: engine.value, whisper_model_size: model.value })
    savedEngine.value = saved.transcriber_type
    savedModel.value = saved.whisper_model_size
    message.value = '转写配置已保存，下次生成笔记时使用。'
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    saving.value = false
  }
}

async function download() {
  downloading.value = true
  message.value = error.value = ''
  try {
    await api.downloadTranscriberModel({ transcriber_type: engine.value, model_size: model.value })
    message.value = '已提交下载，请等待模型状态更新。下载期间可以离开此页。'
    await refreshStatus()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  await load()
  if (!disposed) timer = window.setTimeout(pollStatus, 3000)
})
onUnmounted(() => {
  disposed = true
  window.clearTimeout(timer)
})
</script>

<template>
  <section class="space-y-4" aria-labelledby="transcriber-heading">
    <h2 id="transcriber-heading" class="text-[16px] font-semibold">转写引擎</h2>
    <p class="text-[12px] leading-6 text-muted">选择课程音频的转写方式。本地引擎需要下载模型，在线引擎需要联网。</p>
    <p v-if="loading" class="text-sm text-muted" role="status">正在读取转写配置…</p>
    <template v-else-if="config">
      <fieldset class="grid grid-cols-1 gap-2 sm:grid-cols-2" :disabled="saving || downloading">
        <legend class="mb-2 text-[12px] text-muted">转写方式</legend>
        <label v-for="item in config.available_types" :key="item.value" class="flex items-center gap-3 rounded-xl border p-4 text-[12px]"
          :class="[engine === item.value ? 'border-accent bg-accent-soft' : 'border-line bg-surface', item.value === 'mlx-whisper' && !config.mlx_whisper_available ? 'cursor-not-allowed opacity-50' : 'cursor-pointer']">
          <input v-model="engine" type="radio" name="transcriber-engine" :value="item.value" :disabled="item.value === 'mlx-whisper' && !config.mlx_whisper_available" class="accent-[var(--color-accent)]" />
          <span>{{ item.label }}<small v-if="item.value === savedEngine" class="ml-2 text-accent">已保存</small></span>
        </label>
      </fieldset>
      <div v-if="local" class="rounded-xl border border-line bg-surface p-4 space-y-3">
        <label class="flex items-center gap-3 text-[12px]">本地模型
          <select v-model="model" aria-label="转写模型" :disabled="saving || downloading" class="h-9 min-w-0 flex-1 rounded-lg border border-line bg-surface-2 px-3 text-ink">
            <option v-for="size in config.whisper_model_sizes" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>
        <p class="text-[11px] leading-6 text-muted">tiny 下载较小、转写较快；较大的模型通常更准确，也需要更多内存与时间。</p>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span class="text-[12px]" :class="currentStatus?.failed ? 'text-red-600' : 'text-muted'" role="status">
            {{ currentStatus?.downloaded ? '模型已下载，可使用' : currentStatus?.downloading ? '正在下载，状态每 3 秒更新…' : currentStatus?.failed ? '下载失败，可以重试' : '模型尚未下载' }}
          </span>
          <button class="rounded-lg border border-accent px-3 py-2 text-[12px] text-accent disabled:opacity-50" :disabled="downloading || currentStatus?.downloading || currentStatus?.downloaded" @click="download">
            {{ downloading ? '提交中…' : currentStatus?.downloading ? '下载中…' : currentStatus?.downloaded ? '已下载' : currentStatus?.failed ? '重试下载' : '下载模型' }}
          </button>
        </div>
        <p v-if="currentStatus?.error" class="whitespace-pre-wrap break-words text-[11px] leading-6 text-red-600" role="alert">{{ currentStatus.error }}</p>
      </div>
      <div v-else class="rounded-xl border border-line bg-surface p-4 text-[12px] leading-6 text-muted">
        <template v-if="engine === 'groq'">Groq 需要先在<button class="mx-1 text-accent underline" @click="$emit('open-models')">模型服务</button>中配置 Groq 供应商的 API Key。</template>
        <template v-else>此引擎通过在线服务转写，无需下载本地模型。转写时会上传课程音频，请确保网络可用。</template>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <button class="rounded-lg bg-accent px-4 py-2.5 text-[12px] text-white disabled:opacity-50" :disabled="saving || downloading || !hasChanges" @click="save">{{ saving ? '保存中…' : '保存转写配置' }}</button>
        <span v-if="hasChanges" class="text-[11px] text-muted">有尚未保存的修改</span>
      </div>
      <p v-if="message" class="text-[12px] text-success" role="status">{{ message }}</p>
    </template>
    <p v-if="error" class="text-[12px] text-red-600" role="alert">{{ error }} <button class="underline" @click="retry">重试读取</button></p>
  </section>
</template>
