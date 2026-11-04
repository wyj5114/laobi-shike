import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function mathPlugin(md: MarkdownIt) {
  md.inline.ruler.before('escape', 'math_inline', (state, silent) => {
    const start = state.pos
    if (state.src.charCodeAt(start) !== 0x24) return false
    const isBlock = state.src.charCodeAt(start + 1) === 0x24
    const open = isBlock ? 2 : 1
    let end = start + open
    const closer = isBlock ? '$$' : '$'
    while ((end = state.src.indexOf(closer, end)) !== -1) {
      if (state.src.charCodeAt(end - 1) !== 0x5c) break
      end += open
    }
    if (end === -1) return false
    const content = state.src.slice(start + open, end).trim()
    if (!content) return false
    if (!silent) {
      const token = state.push(isBlock ? 'math_block_inline' : 'math_inline', 'math', 0)
      token.content = content
      token.markup = closer
    }
    state.pos = end + open
    return true
  })

  md.renderer.rules.math_inline = (tokens, idx) => {
    try {
      return katex.renderToString(tokens[idx].content, { throwOnError: false })
    } catch {
      return tokens[idx].content
    }
  }
  md.renderer.rules.math_block_inline = (tokens, idx) => {
    try {
      return katex.renderToString(tokens[idx].content, { throwOnError: false, displayMode: true })
    } catch {
      return tokens[idx].content
    }
  }
}

function headingPlugin(md: MarkdownIt) {
  md.renderer.rules.heading_open = (tokens, idx, options, env, self) => {
    const scope = env as { headingIndex?: number }
    if (scope.headingIndex == null) scope.headingIndex = 0
    tokens[idx].attrSet('id', `heading-${scope.headingIndex++}`)
    return self.renderToken(tokens, idx, options)
  }
}

export function extractHeadings(markdown: string): Array<{ id: string; text: string; level: number }> {
  const headings: Array<{ id: string; text: string; level: number }> = []
  let index = 0
  let inFence = false
  for (const line of markdown.split('\n')) {
    if (/^\s*```/.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue
    const match = line.match(/^(#{1,3})\s+(.+?)\s*#*\s*$/)
    if (!match) continue
    headings.push({
      id: `heading-${index++}`,
      level: match[1].length,
      text: match[2].trim(),
    })
  }
  return headings
}

export function createMarkdownRenderer(): MarkdownIt {
  const md = new MarkdownIt({ html: false, linkify: true })
  md.use(mathPlugin)
  md.use(headingPlugin)
  return md
}
