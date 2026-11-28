export type SessionSummary = {
  id: string
  title: string
  updated_at: number
}

export type Role = 'user' | 'agent' | 'tool' | 'error'

export type ChatMessage = {
  id: string
  role: Role
  text: string
  attachments: string[]
}

/** バックエンドが SSE で送ってくるイベント */
export type StreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'tool'; name: string }
  | { type: 'error'; message: string }
  | { type: 'done' }
