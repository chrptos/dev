import { describe, expect, it } from 'vitest'
import { readEvents, SseParser } from './sse'

describe('SseParser', () => {
  it('イベントが塊の途中で切れても、つなげて読む', () => {
    const p = new SseParser()
    expect(p.push('data: {"type":"del')).toEqual([])
    expect(p.push('ta","text":"あ"}\n')).toEqual([])
    expect(p.push('\ndata: {"type":"done"}\n\n')).toEqual([
      { type: 'delta', text: 'あ' },
      { type: 'done' },
    ])
  })

  it('CRLF と壊れたイベントを扱える', () => {
    const p = new SseParser()
    expect(p.push('data: not json\r\n\r\ndata: {"type":"tool","name":"x"}\r\n\r\n')).toEqual([
      { type: 'tool', name: 'x' },
    ])
  })
})

describe('readEvents', () => {
  it('マルチバイト文字がバイトの途中で分かれても化けない', async () => {
    const bytes = new TextEncoder().encode('data: {"type":"delta","text":"求人"}\n\n')
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        // 「求」の途中で分ける
        controller.enqueue(bytes.slice(0, 32))
        controller.enqueue(bytes.slice(32))
        controller.close()
      },
    })
    const events = []
    for await (const ev of readEvents(stream)) events.push(ev)
    expect(events).toEqual([{ type: 'delta', text: '求人' }])
  })
})
