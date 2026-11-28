import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api/client'
import type { ChatMessage, Role, SessionSummary } from '../types'

let nextId = 0
const newId = () => `m${++nextId}`

function message(role: Role, text: string, attachments: string[] = []): ChatMessage {
  return { id: newId(), role, text, attachments }
}

export function useChat() {
  const [user, setUser] = useState<string | null>(null)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  // 送信中に別の会話へ切り替えたら、届いた返答を表示しない
  const activeId = useRef<string | null>(null)

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
      setLoadError(null)
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    api.getMe().then(setUser, () => setUser(null))
    void refreshSessions()
  }, [refreshSessions])

  const openSession = useCallback(async (id: string) => {
    activeId.current = id
    setCurrentId(id)
    setMessages([])
    try {
      const history = await api.getHistory(id)
      if (activeId.current !== id) return
      setMessages(history.map((m) => message(m.role, m.text, m.attachments)))
    } catch (e) {
      setMessages([message('error', e instanceof Error ? e.message : String(e))])
    }
  }, [])

  const newChat = useCallback(() => {
    activeId.current = null
    setCurrentId(null)
    setMessages([])
  }, [])

  const removeSession = useCallback(
    async (id: string) => {
      await api.deleteSession(id)
      if (activeId.current === id) newChat()
      await refreshSessions()
    },
    [newChat, refreshSessions],
  )

  const send = useCallback(
    async (text: string, file: File | null) => {
      if (sending || (!text.trim() && !file)) return
      setSending(true)
      setMessages((prev) => [...prev, message('user', text.trim(), file ? [file.name] : [])])
      try {
        let id = activeId.current
        if (!id) {
          id = await api.createSession()
          activeId.current = id
          setCurrentId(id)
        }
        // ツールの呼び出しをはさむと、その後の文章は新しい吹き出しにする
        let streamingId: string | null = null
        for await (const ev of api.sendMessage(id, text.trim(), file)) {
          if (activeId.current !== id) break
          if (ev.type === 'delta') {
            if (streamingId === null) {
              const m = message('agent', ev.text)
              streamingId = m.id
              setMessages((prev) => [...prev, m])
            } else {
              const target = streamingId
              setMessages((prev) =>
                prev.map((m) => (m.id === target ? { ...m, text: m.text + ev.text } : m)),
              )
            }
          } else if (ev.type === 'tool') {
            streamingId = null
            setMessages((prev) => [...prev, message('tool', ev.name)])
          } else if (ev.type === 'error') {
            setMessages((prev) => [...prev, message('error', ev.message)])
          }
        }
      } catch (e) {
        setMessages((prev) => [...prev, message('error', e instanceof Error ? e.message : String(e))])
      } finally {
        setSending(false)
        void refreshSessions()
      }
    },
    [sending, refreshSessions],
  )

  return {
    user,
    sessions,
    currentId,
    messages,
    sending,
    loadError,
    openSession,
    newChat,
    removeSession,
    send,
  }
}
