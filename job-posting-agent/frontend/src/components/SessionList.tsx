import type { SessionSummary } from '../types'

type Props = {
  sessions: SessionSummary[]
  currentId: string | null
  onOpen: (id: string) => void
  onDelete: (id: string) => void
}

export function SessionList({ sessions, currentId, onOpen, onDelete }: Props) {
  return (
    <ul className="sessions">
      {sessions.map((s) => (
        <li key={s.id} className={s.id === currentId ? 'active' : undefined}>
          <button className="open" onClick={() => onOpen(s.id)} title={s.title}>
            {s.title}
          </button>
          <button
            className="del"
            aria-label={`「${s.title}」を削除`}
            onClick={() => {
              if (confirm('この会話を削除しますか？元に戻せません。')) onDelete(s.id)
            }}
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  )
}
