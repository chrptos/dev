import type { ChatMessage, SessionSummary, StreamEvent } from '../types'
import { readEvents } from './sse'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// 変更系のリクエストには独自ヘッダーを付ける。バックエンドはこれがないと 403 を返す（CSRF 対策）
const HEADERS = { 'X-Requested-With': 'fetch' }

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(path, { ...init, headers: { ...HEADERS, ...init.headers } })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // JSON でなければ statusText を使う
    }
    throw new ApiError(res.status, detail || `HTTP ${res.status}`)
  }
  return res
}

export async function getMe(): Promise<string> {
  const res = await request('/api/me')
  return ((await res.json()) as { user: string }).user
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await request('/api/sessions')
  return (await res.json()) as SessionSummary[]
}

export async function createSession(): Promise<string> {
  const res = await request('/api/sessions', { method: 'POST' })
  return ((await res.json()) as { id: string }).id
}

export async function deleteSession(id: string): Promise<void> {
  await request(`/api/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

type HistoryMessage = Omit<ChatMessage, 'id'>

export async function getHistory(id: string): Promise<HistoryMessage[]> {
  const res = await request(`/api/sessions/${encodeURIComponent(id)}`)
  return ((await res.json()) as { messages: HistoryMessage[] }).messages
}

export async function* sendMessage(
  sessionId: string,
  text: string,
  file: File | null,
): AsyncGenerator<StreamEvent> {
  const form = new FormData()
  form.append('text', text)
  if (file) form.append('file', file)
  const res = await request(`/api/sessions/${encodeURIComponent(sessionId)}/messages`, {
    method: 'POST',
    body: form,
  })
  if (!res.body) throw new ApiError(500, '返答を受け取れませんでした')
  yield* readEvents(res.body)
}
