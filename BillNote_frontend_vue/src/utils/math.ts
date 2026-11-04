import type MarkdownIt from 'markdown-it'
import katex from 'katex'

function isEscaped(source: string, position: number): boolean {
  let backslashes = 0
  for (let index = position - 1; index >= 0 && source[index] === '\\'; index--) backslashes++
  return backslashes % 2 === 1
}

export function mathPlugin(md: MarkdownIt) {
  md.inline.ruler.before('escape', 'math_inline', (state, silent) => {
    const start = state.pos
    const prefix = state.src.slice(start, start + 2)
    const display = prefix === '$$' || prefix === '\\['
    const opener = display || prefix === '\\(' ? prefix : state.src[start] === '$' ? '$' : ''
    if (!opener) return false
    const closer = opener === '\\(' ? '\\)' : opener === '\\[' ? '\\]' : opener
    let end = start + opener.length
    while ((end = state.src.indexOf(closer, end)) !== -1) {
      if (!isEscaped(state.src, end)) break
      end += closer.length
    }
    if (end === -1) return false
    const content = state.src.slice(start + opener.length, end).trim()
    if (!content) return false
    if (!silent) {
      const token = state.push(display ? 'math_display_inline' : 'math_inline', 'math', 0)
      token.content = content
      token.markup = opener
    }
    state.pos = end + closer.length
    return true
  })

  md.block.ruler.before('fence', 'math_block', (state, start, end, silent) => {
    if (state.sCount[start] - state.blkIndent >= 4) return false
    const first = state.src.slice(state.bMarks[start] + state.tShift[start], state.eMarks[start])
    const opener = first.slice(0, 2)
    if (opener !== '$$' && opener !== '\\[') return false
    const closer = opener === '$$' ? '$$' : '\\]'
    const lines: string[] = []
    for (let line = start; line < end; line++) {
      if (line > start && !state.isEmpty(line) && state.sCount[line] < state.blkIndent) break
      const text = line === start ? first.slice(2) : state.src.slice(state.bMarks[line] + state.tShift[line], state.eMarks[line])
      const close = text.indexOf(closer)
      if (close !== -1 && !isEscaped(text, close)) {
        if (text.slice(close + closer.length).trim()) return false
        lines.push(text.slice(0, close))
        if (!lines.join('\n').trim()) return false
        if (silent) return true
        const token = state.push('math_block', 'math', 0)
        token.block = true
        token.content = lines.join('\n').trim()
        token.map = [start, line + 1]
        token.markup = opener
        state.line = line + 1
        return true
      }
      lines.push(text)
    }
    return false
  }, { alt: ['paragraph', 'reference', 'blockquote', 'list'] })

  function renderMath(source: string, displayMode: boolean) {
    try {
      return katex.renderToString(source, { displayMode, throwOnError: false, trust: false })
    } catch {
      return `<code class="math-error">${md.utils.escapeHtml(source)}</code>`
    }
  }

  md.renderer.rules.math_inline = (tokens, index) => renderMath(tokens[index].content, false)
  md.renderer.rules.math_display_inline = (tokens, index) => renderMath(tokens[index].content, true)
  md.renderer.rules.math_block = (tokens, index) => `<p class="math-block">${renderMath(tokens[index].content, true)}</p>\n`
}
