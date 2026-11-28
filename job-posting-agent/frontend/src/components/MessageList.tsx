import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import { Markdown } from './Markdown'

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: 'end' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="messages">
        <div className="empty">
          求人ID、URL、本文の貼り付け、または PDF の添付で始めます。
          <br />
          例：「求人ID J-001 をまとめて、標準の観点でネクストアクションを出して」
        </div>
      </div>
    )
  }

  return (
    <div className="messages" aria-live="polite">
      {messages.map((m) => {
        switch (m.role) {
          case 'tool':
            return (
              <div key={m.id} className="status">
                🔧 {m.text}
              </div>
            )
          case 'error':
            return (
              <div key={m.id} className="status error" role="alert">
                {m.text}
              </div>
            )
          case 'agent':
            return (
              <div key={m.id} className="msg agent md">
                <Markdown text={m.text} />
              </div>
            )
          default:
            return (
              <div key={m.id} className="msg user">
                {m.attachments.map((a) => (
                  <div key={a} className="att">
                    📎 {a}
                  </div>
                ))}
                {m.text}
              </div>
            )
        }
      })}
      <div ref={bottom} />
    </div>
  )
}
