<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { builtInPlugins, Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { mathPlugin } from '@/utils/math'
import 'katex/dist/katex.min.css'

const props = defineProps<{ markdown: string }>()
const svg = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null
const transformer = new Transformer(builtInPlugins.filter(plugin => plugin.name !== 'katex'))
transformer.md.set({ html: false })
transformer.md.use(mathPlugin)

async function render() {
  if (!svg.value) return
  const { root } = transformer.transform(props.markdown || '# 暂无内容')
  mm?.destroy()
  const instance = new Markmap(svg.value, { autoFit: true, duration: 0, maxWidth: 640, spacingVertical: 14 })
  mm = instance
  await instance.setData(root)
  await document.fonts.ready
  if (mm === instance) await instance.fit()
}

onMounted(render)
watch(() => props.markdown, render)
onBeforeUnmount(() => {
  mm?.destroy()
  mm = null
})
</script>

<template>
  <div class="mindmap-view h-full w-full overflow-hidden rounded-[12px] border border-line bg-surface">
    <svg ref="svg" class="h-full w-full" />
  </div>
</template>

<style scoped>
.mindmap-view :deep(.markmap-foreign p) {
  margin: 0;
}
.mindmap-view :deep(.katex-display) {
  margin: .5em 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: .2em 0;
}
.mindmap-view :deep(.katex) {
  font-size: 1.1em;
}
</style>
