import { Composer } from './components/Composer'
import { MessageList } from './components/MessageList'
import { SessionList } from './components/SessionList'
import { useChat } from './hooks/useChat'

export default function App() {
  const chat = useChat()

  return (
    <div className="app">
      <aside>
        <header>
          <button className="primary" onClick={chat.newChat}>
            ＋ 新しい会話
          </button>
          {chat.user && <div className="me">{chat.user}</div>}
        </header>
        {chat.loadError && (
          <div className="status error" role="alert">
            {chat.loadError}
          </div>
        )}
        <SessionList
          sessions={chat.sessions}
          currentId={chat.currentId}
          onOpen={(id) => void chat.openSession(id)}
          onDelete={(id) => void chat.removeSession(id)}
        />
      </aside>
      <main>
        <MessageList messages={chat.messages} />
        <Composer disabled={chat.sending} onSend={(text, file) => void chat.send(text, file)} />
      </main>
    </div>
  )
}
