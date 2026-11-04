const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api'

interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  const json = (await res.json()) as ApiResponse<T>
  if (!res.ok || json.code !== 0) {
    throw new Error(json.msg || `请求失败 (${res.status})`)
  }
  return json.data
}

export interface ApiGroup {
  id: string
  name: string
  order: number
  count: number
}

export interface ApiTranscriptSegment {
  start: number
  end: number
  text: string
}

export interface ApiTranscript {
  language?: string
  full_text?: string
  segments?: ApiTranscriptSegment[]
}

export interface ApiNote {
  id: string
  video_id: string
  platform: string
  title: string
  duration: number
  cover_url: string | null
  group_id: string | null
  status: string
  created_at: string | null
  updated_at: string | null
  markdown?: string
  transcript?: ApiTranscript
  audio_meta?: {
    title?: string
    duration?: number
    cover_url?: string
    video_id?: string
    raw_info?: { uploader?: string }
  }
}

export interface ApiProvider {
  id: string
  name: string
  type: string
  enabled: number
  base_url: string
  api_key: string
}

export interface ApiModel {
  id: string | number
  model_name?: string
  name?: string
}

export interface TaskStatus {
  status: string
  message?: string
  logs?: Array<{ time: string; status: string; message: string }>
  result?: {
    markdown?: string
    transcript?: unknown
    audio_meta?: {
      title?: string
      duration?: number
      cover_url?: string
      video_id?: string
    }
  }
}

export interface ApiChatSource {
  text: string
  source_type: string
  section_title?: string
  start_time?: number
  end_time?: number
}

export interface ApiCollectionItem {
  video_id: string
  bvid: string
  page?: number
  title: string
  duration: number
  url: string
  generated: boolean
}

export interface ApiCollection {
  kind: 'pages' | 'season' | 'series' | 'single'
  title: string
  total: number
  items: ApiCollectionItem[]
}

export interface ApiMedia {
  path: string
  name: string
  kind: 'video' | 'audio' | 'image'
  size: number
  modified: number
  url: string
}

export interface ChatStreamHandlers {
  onSources?: (sources: ApiChatSource[]) => void
  onToken?: (delta: string) => void
  onDone?: (answer: string) => void
  onError?: (message: string) => void
}

export async function chatAskStream(
  payload: {
    task_id: string
    question: string
    history: Array<{ role: string; content: string }>
    provider_id: string
    model_name: string
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
) {
  const res = await fetch(`${BASE}/chat/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `请求失败 (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const dispatch = (block: string) => {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    let data: any
    try {
      data = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (event === 'sources') handlers.onSources?.(data.sources || [])
    else if (event === 'token') handlers.onToken?.(data.delta || '')
    else if (event === 'done') handlers.onDone?.(data.answer || '')
    else if (event === 'error') handlers.onError?.(data.message || '问答失败')
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let split = buffer.indexOf('\n\n')
    while (split !== -1) {
      dispatch(buffer.slice(0, split))
      buffer = buffer.slice(split + 2)
      split = buffer.indexOf('\n\n')
    }
  }
  if (buffer.trim()) dispatch(buffer)
}

export const api = {
  listGroups: () => request<ApiGroup[]>('/groups'),
  createGroup: (name: string) =>
    request<ApiGroup>('/groups', { method: 'POST', body: JSON.stringify({ name }) }),
  updateGroup: (id: string, payload: { name?: string; order?: number }) =>
    request<ApiGroup>(`/groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteGroup: (id: string) => request<null>(`/groups/${id}`, { method: 'DELETE' }),

  listNotes: (params?: { q?: string; group_id?: string; status?: string; page?: number; page_size?: number }) => {
    const search = new URLSearchParams()
    if (params?.q) search.set('q', params.q)
    if (params?.group_id) search.set('group_id', params.group_id)
    if (params?.status) search.set('status', params.status)
    if (params?.page) search.set('page', String(params.page))
    if (params?.page_size) search.set('page_size', String(params.page_size))
    const suffix = search.toString() ? `?${search.toString()}` : ''
    return request<{ items: ApiNote[]; total: number; page: number; page_size: number }>(`/notes${suffix}`)
  },
  getNote: (id: string) => request<ApiNote>(`/notes/${id}`),
  exportGroup: async (groupId: string) => {
    const res = await fetch(`${BASE}/notes/export?group_id=${encodeURIComponent(groupId)}`)
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `导出失败 (${res.status})`)
    }
    return await res.blob()
  },
  moveNote: (id: string, groupId: string | null) =>
    request<ApiNote>(`/notes/${id}`, { method: 'PATCH', body: JSON.stringify({ group_id: groupId }) }),
  deleteNote: (id: string) => request<null>(`/notes/${id}`, { method: 'DELETE' }),

  listProviders: () => request<ApiProvider[]>('/get_all_providers'),
  addProvider: (payload: { name: string; api_key: string; base_url: string; logo?: string; type?: string }) =>
    request<unknown>('/add_provider', { method: 'POST', body: JSON.stringify(payload) }),
  listModels: (providerId: string) =>
    request<{ models: ApiModel[]; error?: string }>(`/model_list/${providerId}`),
  listEnabledModels: (providerId: string) => request<ApiModel[]>(`/model_enable/${providerId}`),
  addModel: (providerId: string, modelName: string) =>
    request<unknown>('/models', { method: 'POST', body: JSON.stringify({ provider_id: providerId, model_name: modelName }) }),
  deleteModel: (modelId: number | string) => request<unknown>(`/models/delete/${modelId}`),
  updateProvider: (payload: { id: string; api_key?: string; base_url?: string; name?: string; enabled?: number }) =>
    request<unknown>('/update_provider', { method: 'POST', body: JSON.stringify(payload) }),
  connectTest: (id: string, model?: string) =>
    request<boolean>('/connect_test', { method: 'POST', body: JSON.stringify({ id, model }) }),

  generateNote: (payload: {
    video_url: string
    platform: string
    quality: string
    model_name: string
    provider_id: string
    style?: string
    format?: string[]
    screenshot?: boolean
    link?: boolean
    group_id?: string
  }) => request<{ task_id: string }>('/generate_note', { method: 'POST', body: JSON.stringify(payload) }),
  getCollection: (url: string) =>
    request<ApiCollection>(`/bilibili/collection?url=${encodeURIComponent(url)}`),
  generateBatch: (payload: {
    items: Array<{ video_url: string; title?: string }>
    platform: string
    quality: string
    model_name: string
    provider_id: string
    style?: string
    format?: string[]
    group_id?: string
    batch_concurrency: number
  }) => request<{ task_ids: string[]; count: number; concurrency: number }>('/generate_batch', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  taskStatus: (taskId: string) => request<TaskStatus>(`/task_status/${taskId}`),

  chatStatus: (taskId: string) =>
    request<{ status: string; indexed: boolean }>(`/chat/status?task_id=${encodeURIComponent(taskId)}`),
  chatIndex: (taskId: string) =>
    request<null>('/chat/index', { method: 'POST', body: JSON.stringify({ task_id: taskId }) }),
  chatAsk: (payload: {
    task_id: string
    question: string
    history: Array<{ role: string; content: string }>
    provider_id: string
    model_name: string
  }) => request<{ answer: string; sources: ApiChatSource[] }>('/chat/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  listMedia: () => request<{ items: ApiMedia[]; count: number; total_size: number }>('/media'),
  deleteMedia: (path: string) =>
    request<{ freed: number }>(`/media/${path.split('/').map(encodeURIComponent).join('/')}`, { method: 'DELETE' }),
  cleanMedia: () => request<{ deleted: number; freed: number }>('/media', { method: 'DELETE' }),
}
