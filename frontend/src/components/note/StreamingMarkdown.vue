<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { createMarkdownRenderer } from '@/utils/markdown'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const md = createMarkdownRenderer()
const html = ref('')
let timer: number | undefined

/** 流式过程中补全未闭合的代码块，避免渲染成半截 HTML。 */
function normalize(content: string): string {
  const fences = (content.match(/```/g) || []).length
  return fences % 2 === 1 ? `${content}\n\`\`\`` : content
}

function render() {
  html.value = md.render(normalize(props.content))
}

watch(
  () => props.content,
  () => {
    if (timer) return
    // 约 50ms 合并一次 token，既跟手又避免每个字符都整篇重排
    timer = window.setTimeout(() => {
      timer = undefined
      render()
    }, 50)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (timer) window.clearTimeout(timer)
})
</script>

<template>
  <div class="streaming-markdown article-body text-[13px] leading-6">
    <div v-html="html" />
    <span v-if="streaming" class="streaming-caret" />
  </div>
</template>

<style scoped>
.streaming-markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.streaming-caret {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--color-accent);
  animation: caret-blink 0.9s steps(2, start) infinite;
}
@keyframes caret-blink {
  to {
    visibility: hidden;
  }
}
</style>
