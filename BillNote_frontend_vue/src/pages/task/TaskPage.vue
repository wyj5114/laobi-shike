<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CircleCheck, CircleDashed, LoaderCircle, XCircle } from 'lucide-vue-next'
import { useLibraryStore } from '@/stores/library'
import { api } from '@/services/api'
import RetryTaskForm from '@/components/note/RetryTaskForm.vue'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()

const demoIds = ['demo', 'prob-6', 'tcp', 'english-3']
const isDemo = demoIds.includes(String(route.params.id))
const remoteStatus = ref('')
const remoteTitle = ref('')
const remoteMessage = ref('')
const remoteLogs = ref<Array<{ time: string; status: string; message: string }>>([])
let timer: number | undefined

const note = computed(
  () =>
    library.notes.find(n => n.id === route.params.id) ?? {
      id: String(route.params.id),
      title: remoteTitle.value || '正在解析 B 站视频…',
      author: 'B 站',
      duration: '--:--',
      status: 'running' as const,
    },
)

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    SUCCESS: '已完成',
    FAILED: '失败',
    PENDING: '排队中',
    PARSING: '解析中',
    DOWNLOADING: '下载中',
    TRANSCRIBING: '转写中',
    SUMMARIZING: '生成笔记',
    SAVING: '保存中',
  }
  if (remoteStatus.value) return labels[remoteStatus.value] || '处理中'
  return note.value.status === 'done' ? '已完成' : note.value.status === 'failed' ? '失败' : '转写中'
})

const isDone = computed(() =>
  remoteStatus.value ? remoteStatus.value === 'SUCCESS' : note.value.status === 'done',
)
const isFailed = computed(() =>
  remoteStatus.value ? remoteStatus.value === 'FAILED' : note.value.status === 'failed',
)

const currentIndex = computed(() => {
  if (isDone.value) return 5
  const map: Record<string, number> = {
    PENDING: 0,
    PARSING: 0,
    DOWNLOADING: 1,
    TRANSCRIBING: 2,
    SUMMARIZING: 3,
    SAVING: 4,
  }
  const lastStage = [...remoteLogs.value].reverse().find(item => item.status in map)?.status
  return map[isFailed.value ? lastStage ?? 'PARSING' : remoteStatus.value] ?? 0
})

const stages = computed(() => {
  const stageStatus: Record<string, string[]> = {
    parse: ['PENDING', 'PARSING'],
    download: ['DOWNLOADING'],
    transcribe: ['TRANSCRIBING'],
    summarize: ['SUMMARIZING'],
    save: ['SAVING', 'SUCCESS'],
  }
  const states = [
    { key: 'parse', label: '解析视频', detail: '获取视频信息与字幕' },
    { key: 'download', label: '下载音频', detail: 'B 站音频流' },
    { key: 'transcribe', label: '语音转写', detail: '使用设置中选择的转写引擎' },
    { key: 'summarize', label: '生成笔记', detail: 'LLM 生成笔记' },
    { key: 'save', label: '保存', detail: '写入笔记库与向量索引' },
  ]
  return states.map((stage, idx) => {
    const log = remoteLogs.value.find(item => stageStatus[stage.key].includes(item.status))
    return {
      ...stage,
      time: log?.time || '--:--',
      state: idx < currentIndex.value ? 'done' : idx === currentIndex.value ? 'running' : 'waiting',
    }
  })
})

const logs = computed(() => {
  if (remoteLogs.value.length) {
    return remoteLogs.value.map(item => [
      item.time,
      `${item.status}${item.message ? ` · ${item.message}` : ''}`,
    ])
  }
  if (remoteMessage.value) return [['--:--', remoteMessage.value]]
  return [['--:--', remoteStatus.value ? `status=${remoteStatus.value}` : '暂无日志']]
})

async function refresh() {
  if (isDemo) return
  try {
    const data = await api.taskStatus(String(route.params.id))
    remoteStatus.value = data.status
    remoteMessage.value = data.message || ''
    remoteLogs.value = data.logs || []
    if (data.result?.audio_meta?.title) remoteTitle.value = data.result.audio_meta.title
    if (data.status === 'SUCCESS') await library.load()
  } catch (error) {
    remoteMessage.value = error instanceof Error ? error.message : String(error)
  }
}

onMounted(() => {
  refresh()
  if (!isDemo) timer = window.setInterval(refresh, 2000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="page-frame task-detail-page">
      <button class="mb-5 flex items-center gap-1.5 text-[12.5px] text-muted hover:text-ink" @click="router.push('/library')">
        <ArrowLeft :size="14" /> 返回笔记库
      </button>

      <div class="flex items-start justify-between border-b border-line pb-5">
        <div>
          <p class="text-[11.5px] uppercase tracking-[.16em] text-accent">Task</p>
          <h1 class="mt-2 text-[27px] font-semibold tracking-[-0.025em]">{{ note?.title ?? '任务详情' }}</h1>
          <div class="mt-2 flex items-center gap-2 text-[12.5px] text-muted">
            <span>{{ note?.author }}</span>
            <span class="h-[3px] w-[3px] rounded-full bg-line" />
            <span>{{ note?.duration }}</span>
            <span class="h-[3px] w-[3px] rounded-full bg-line" />
            <span>task_id · {{ route.params.id }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span
            class="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px]"
            :class="isDone ? 'bg-emerald-50 text-success' : isFailed ? 'bg-red-50 text-red-600' : 'bg-accent-soft text-accent'"
          >
            <LoaderCircle v-if="!isDone && !isFailed" :size="13" class="animate-spin" />
            <CircleCheck v-else-if="isDone" :size="13" />
            <XCircle v-else :size="13" />
            {{ statusLabel }}
          </span>
        </div>
      </div>

      <div v-if="isFailed" class="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-xs leading-6 text-red-700" role="alert"><strong>任务未完成</strong><p class="break-words">{{ remoteMessage }}</p></div>
      <RetryTaskForm v-if="isFailed && !isDemo" :task-id="String(route.params.id)" @queued="refresh(); library.load()" />

      <div class="mt-7 flex flex-col gap-7 xl:flex-row">
        <!-- 阶段时间线 -->
        <section class="glass-card w-full shrink-0 rounded-[14px] p-6 xl:w-[480px]">
          <h2 class="text-[15px] font-semibold">执行进度</h2>
          <div class="mt-5">
            <div v-for="(stage, idx) in stages" :key="stage.key" class="relative flex gap-4 pb-7 last:pb-0">
              <div v-if="idx < stages.length - 1" class="absolute left-[11px] top-6 h-full w-px bg-line" />
              <div class="relative z-10 mt-0.5">
                <CircleCheck v-if="stage.state === 'done'" :size="23" class="text-success" :stroke-width="1.8" />
                <XCircle v-else-if="stage.state === 'running' && isFailed" :size="23" class="text-red-600" :stroke-width="1.8" />
                <LoaderCircle v-else-if="stage.state === 'running'" :size="23" class="animate-spin text-accent" :stroke-width="1.8" />
                <CircleDashed v-else :size="23" class="text-line" :stroke-width="1.8" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between">
                  <p class="text-[14px] font-medium" :class="stage.state === 'waiting' ? 'text-faint' : 'text-ink'">{{ stage.label }}</p>
                  <span class="text-[11.5px] text-faint">{{ stage.time }}</span>
                </div>
                <p class="mt-1 text-[12px] text-muted">{{ stage.detail }}</p>
                <div v-if="stage.state === 'running' && !isFailed" class="mt-2.5 h-1 overflow-hidden rounded-full bg-surface-2">
                  <div class="h-full w-1/2 animate-pulse rounded-full bg-accent" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 日志 -->
        <section class="glass-card min-w-0 flex-1 rounded-[14px]">
          <div class="flex items-center justify-between border-b border-line px-5 py-3">
            <h2 class="text-[13.5px] font-medium">实时日志</h2>
            <span class="text-[11px] text-faint">自动滚动</span>
          </div>
          <div class="break-words p-5 font-mono text-[12px] leading-7 text-muted">
            <p v-for="[time, line] in logs" :key="time + line">
              <span class="text-faint">{{ time }}</span>
              <span class="ml-3">{{ line }}</span>
            </p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
