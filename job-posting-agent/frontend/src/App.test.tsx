import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

type Route = (init: RequestInit | undefined) => Response

function sse(...events: object[]): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new Response(body, { headers: { 'Content-Type': 'text/event-stream' } })
}

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })

/** パスとメソッドごとに返す値を決めた、偽の fetch */
function mockFetch(routes: Record<string, Route>) {
  const calls: { key: string; init: RequestInit | undefined }[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${String(input)}`
    calls.push({ key, init })
    const route = routes[key]
    if (!route) return json({ detail: 'not found' }, 404)
    return route(init)
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

describe('App', () => {
  it('送信すると会話を作り、ツールと返答をストリーミングで表示する', async () => {
    let sessions: object[] = []
    const calls = mockFetch({
      'GET /api/me': () => json({ user: 'alice@example.com' }),
      'GET /api/sessions': () => json(sessions),
      'POST /api/sessions': () => {
        sessions = [{ id: 's1', title: '求人ID J-001 をまとめて', updated_at: 1 }]
        return json({ id: 's1' })
      },
      'POST /api/sessions/s1/messages': () =>
        sse(
          { type: 'tool', name: 'fetch_job_posting_from_db' },
          { type: 'delta', text: '## まとめ\n\n' },
          { type: 'delta', text: '- **会社名**: 株式会社サンプル' },
          { type: 'done' },
        ),
    })

    render(<App />)
    expect(await screen.findByText('alice@example.com')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('メッセージ'), '求人ID J-001 をまとめて')
    await userEvent.click(screen.getByRole('button', { name: '送信' }))

    expect(await screen.findByText('🔧 fetch_job_posting_from_db')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'まとめ' })).toBeInTheDocument()
    expect(screen.getByText('会社名').tagName).toBe('STRONG')
    // 会話の一覧が更新される
    expect(await screen.findByRole('button', { name: '求人ID J-001 をまとめて' })).toBeInTheDocument()

    // 変更系のリクエストには CSRF 対策のヘッダーが付く
    const post = calls.find((c) => c.key === 'POST /api/sessions/s1/messages')
    expect(new Headers(post?.init?.headers).get('X-Requested-With')).toBe('fetch')
    const form = post?.init?.body as FormData
    expect(form.get('text')).toBe('求人ID J-001 をまとめて')
  })

  it('過去の会話を開くと履歴を表示する', async () => {
    mockFetch({
      'GET /api/me': () => json({ user: 'alice@example.com' }),
      'GET /api/sessions': () => json([{ id: 's9', title: '以前の会話', updated_at: 1 }]),
      'GET /api/sessions/s9': () =>
        json({
          id: 's9',
          messages: [
            { role: 'user', text: '', attachments: ['job.pdf'] },
            { role: 'agent', text: '**読みました**', attachments: [] },
          ],
        }),
    })

    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: '以前の会話' }))
    expect(await screen.findByText('📎 job.pdf')).toBeInTheDocument()
    expect(screen.getByText('読みました').tagName).toBe('STRONG')
  })

  it('サーバーのエラーを表示し、入力をやり直せる', async () => {
    mockFetch({
      'GET /api/me': () => json({ user: 'alice@example.com' }),
      'GET /api/sessions': () => json([]),
      'POST /api/sessions': () => json({ id: 's1' }),
      'POST /api/sessions/s1/messages': () =>
        json({ detail: '少し時間をおいてから送ってください' }, 429),
    })

    render(<App />)
    await userEvent.type(screen.getByLabelText('メッセージ'), 'hi')
    await userEvent.click(screen.getByRole('button', { name: '送信' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('少し時間をおいてから送ってください')
    await userEvent.type(screen.getByLabelText('メッセージ'), 'again')
    await waitFor(() => expect(screen.getByRole('button', { name: '送信' })).toBeEnabled())
  })
})
