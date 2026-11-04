<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type ApiGenerateNoteRequest, type ApiProvider, type ApiModel } from '@/services/api'

const props = defineProps<{ taskId: string }>()
const emit = defineEmits<{ queued: [] }>()
const original = ref<ApiGenerateNoteRequest | null>(null)
const videoUrl = ref('')
const providers = ref<ApiProvider[]>([])
const providerId = ref('')
const models = ref<ApiModel[]>([])
const model = ref('')
const loading = ref(true)
const modelLoading = ref(false)
const busy = ref(false)
const error = ref('')
const requestNotice = ref('')

async function loadModels(preferred = '') {
  error.value = ''
  modelLoading.value = true
  const requestedProvider = providerId.value
  models.value = []
  model.value = ''
  try {
    let items = await api.listEnabledModels(requestedProvider)
    if (!items.length) items = (await api.listModels(requestedProvider)).models
    if (providerId.value !== requestedProvider) return
    models.value = items
    model.value = items.some(item => String(item.model_name ?? item.id) === preferred) ? preferred : String(items[0]?.model_name ?? items[0]?.id ?? '')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    if (providerId.value === requestedProvider) modelLoading.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  requestNotice.value = ''
  try {
    const [requestResult, providerResult] = await Promise.allSettled([api.getTaskRetryRequest(props.taskId), api.listProviders()])
    if (providerResult.status === 'rejected') throw providerResult.reason
    const list = providerResult.value
    const request = requestResult.status === 'fulfilled' ? requestResult.value : null
    if (requestResult.status === 'rejected') {
      requestNotice.value = '原任务参数暂时无法读取，可补填原视频链接后重试。'
    }
    original.value = request
    videoUrl.value = request?.video_url ?? ''
    providers.value = list.filter(item => item.enabled && item.api_key)
    providerId.value = providers.value.find(item => item.id === request?.provider_id)?.id ?? providers.value[0]?.id ?? ''
    if (providerId.value) await loadModels(request?.model_name)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function retry() {
  if (busy.value || !videoUrl.value.trim() || !model.value) return
  busy.value = true
  error.value = ''
  try {
    await api.generateNote({
      ...(original.value ?? { platform: 'bilibili', quality: 'medium', format: ['目录', 'AI 总结'], style: 'detailed' }),
      video_url: videoUrl.value.trim(), task_id: props.taskId,
      model_name: model.value, provider_id: providerId.value,
    })
    emit('queued')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="mt-5 space-y-3 rounded-xl border border-line bg-surface p-5" aria-label="重试失败任务">
    <h2 class="text-sm font-medium">恢复这个任务</h2>
    <p class="text-xs leading-6 text-muted">重新加入队列后，将复用有效的下载和转写缓存。</p>
    <p v-if="loading" class="text-xs text-muted" role="status">正在读取重试配置…</p>
    <template v-else>
      <p v-if="requestNotice" class="text-xs text-muted" role="status">{{ requestNotice }}</p>
      <p v-else-if="!original" class="text-xs text-muted">这个旧任务尚未保存原始参数，请粘贴准确的原视频链接，合集需包含对应的分 P 参数。</p>
      <label class="block text-xs text-muted">原视频链接<input v-model="videoUrl" :readonly="!!original" :disabled="busy" placeholder="https://www.bilibili.com/video/BV…?p=…" class="mt-2 h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-xs text-ink" /></label>
      <div class="flex flex-wrap gap-2">
        <select v-model="providerId" aria-label="重试供应商" :disabled="busy || modelLoading" class="min-w-0 flex-1 rounded-lg border border-line bg-surface-2 p-2 text-xs" @change="loadModels()"><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option></select>
        <select v-model="model" aria-label="重试生成模型" :disabled="busy || modelLoading" class="min-w-0 flex-1 rounded-lg border border-line bg-surface-2 p-2 text-xs"><option v-if="!models.length" value="">{{ modelLoading ? '读取中…' : '没有可用模型' }}</option><option v-for="item in models" :key="String(item.id)" :value="String(item.model_name ?? item.id)">{{ item.model_name ?? item.id }}</option></select>
      </div>
      <div class="flex flex-wrap items-center gap-4"><button :disabled="busy || modelLoading || !videoUrl.trim() || !model" class="rounded-lg bg-accent px-4 py-2 text-xs text-white disabled:opacity-50" @click="retry">{{ busy ? '加入队列中…' : '重新尝试' }}</button><RouterLink to="/settings?tab=transcriber" class="text-xs text-accent underline">调整转写引擎</RouterLink></div>
      <p v-if="!providers.length && !error" class="text-xs text-muted">请先在模型服务中配置可用供应商。</p>
    </template>
    <p v-if="error" class="break-words text-xs text-red-600" role="alert">{{ error }} <button class="underline" @click="load">重新读取配置</button></p>
  </section>
</template>
