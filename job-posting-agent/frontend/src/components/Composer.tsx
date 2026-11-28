import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

type Props = {
  disabled: boolean
  onSend: (text: string, file: File | null) => void
}

export function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (disabled || (!text.trim() && !file)) return
    onSend(text, file)
    setText('')
    setFile(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
  }

  return (
    <form className="composer" onSubmit={submit}>
      <label className="file" title="PDF を添付">
        📎
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf"
          aria-label="PDF を添付"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      {file && <span className="file-name">{file.name}</span>}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        aria-label="メッセージ"
        placeholder="メッセージ（Enter で改行、Ctrl+Enter / ⌘+Enter で送信）"
      />
      <button className="primary" type="submit" disabled={disabled || (!text.trim() && !file)}>
        送信
      </button>
    </form>
  )
}
