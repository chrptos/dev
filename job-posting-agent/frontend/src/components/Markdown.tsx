import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * エージェントの返答を Markdown として表示する。
 *
 * react-markdown は HTML を解釈せず（rehype-raw を使わない限り文字として表示する）、
 * javascript: などの危険な URL も取り除く。返答には求人ページや PDF の文章が混ざりうるので、
 * 画像も表示しない（仕込まれた画像の URL を通じて会話の内容が外部に送られるのを防ぐ）。
 */
export function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // 画像は読み込まず、代替テキストだけを表示する
        img: ({ alt }) => (alt ? <span className="img-alt">[画像: {alt}]</span> : null),
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  )
}
