import MarkdownIt from 'markdown-it'
import { mathPlugin } from './math'
import 'katex/dist/katex.min.css'

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
