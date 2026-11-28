import type { StreamEvent } from '../types'

/**
 * SSE（`data: {...}\n\n` の繰り返し）を少しずつ受け取り、イベントに分ける。
 * 受け取った塊の境目がイベントの途中でもよいように、残りを持ち越す。
 */
export class SseParser {
  private buffer = ''

  push(chunk: string): StreamEvent[] {
    this.buffer += chunk.replace(/\r\n/g, '\n')
    const events: StreamEvent[] = []
    let idx: number
    while ((idx = this.buffer.indexOf('\n\n')) >= 0) {
      const block = this.buffer.slice(0, idx)
      this.buffer = this.buffer.slice(idx + 2)
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (!data) continue
      try {
        events.push(JSON.parse(data) as StreamEvent)
      } catch {
        // 壊れたイベントは無視する
      }
    }
    return events
  }
}

export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<StreamEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  const parser = new SseParser()
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      yield* parser.push(decoder.decode(value, { stream: true }))
    }
    yield* parser.push(decoder.decode() + '\n\n')
  } finally {
    reader.releaseLock()
  }
}
