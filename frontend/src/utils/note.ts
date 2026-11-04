/** 把 B 站原始标题整理成适合笔记列表/文件名的短标题。 */
export function cleanNoteTitle(raw: string): string {
  if (!raw) return '未命名笔记'
  const text = raw
    // 《高等数学》 -> 高等数学
    .replace(/《([^》]+)》/g, '$1')
    // 【电子】/【宋浩老师】这类标签去掉
    .replace(/[【\[][^】\]]*[】\]]\s*/g, '')
    // 课程营销词
    .replace(/全程教学视频|教学视频|完整版|高清|1080P|4K/gi, '')
    // 去掉 p04 / P12 这类分 P 标记
    .replace(/p\d+\s*/gi, '')
    .replace(/等主讲/g, '')
    .replace(/[\\/:*?"<>|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  return text.length > 40 ? `${text.slice(0, 40)}…` : text || '未命名笔记'
}
