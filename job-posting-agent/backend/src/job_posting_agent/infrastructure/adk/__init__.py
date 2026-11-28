"""ADK（Runner とセッション）を使う実装。ADK の Runner とセッションに触るのはここだけ。"""

# ADK のセッションで、このアプリの会話を区別する名前
APP_NAME = "job_posting_agent"
# 会話の題名を入れるセッションの state のキー
TITLE_KEY = "title"
# 添付ファイルの名前を、メッセージの中に残すときの書き方
ATTACHMENT_PREFIX = "[添付ファイル: "
