<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const props = defineProps<{ markdown: string }>()
const svg = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null

function render() {
  if (!svg.value) return
  const { root } = new Transformer().transform(props.markdown || '# 暂无内容')
  mm?.destroy()
  mm = Markmap.create(svg.value, { autoFit: true, duration: 250 }, root)
}

onMounted(render)
watch(() => props.markdown, render)
onBeforeUnmount(() => mm?.destroy())
</script>

<template>
  <div class="h-full w-full overflow-hidden rounded-[12px] border border-line bg-surface">
    <svg ref="svg" class="h-full w-full" />
  </div>
</template>
