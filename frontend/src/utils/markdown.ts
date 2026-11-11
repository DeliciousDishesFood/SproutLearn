// Markdown 渲染唯一出口：marked 解析后必须经 DOMPurify 净化，才允许 v-html。
import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

export function renderMarkdown(source: string): string {
  if (!source) return ''
  const html = marked.parse(source, { async: false }) as string
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'iframe', 'form', 'input', 'button'],
    FORBID_ATTR: ['style'],
  })
}
