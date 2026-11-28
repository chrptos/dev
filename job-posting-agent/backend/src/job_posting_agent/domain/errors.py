"""サービスが投げるエラー。メッセージは利用者にそのまま見せてよい文にする。

HTTP ステータスやツールの戻り値への変換は、presentation 層で行う。
"""


class DomainError(Exception):
    """利用者に伝えてよいエラーの基底クラス。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Unauthenticated(DomainError):
    """利用者を特定できない。"""


class NotFound(DomainError):
    """対象が見つからない（他人のものも含む）。"""


class InvalidInput(DomainError):
    """入力が決まりに合わない。"""


class PayloadTooLarge(InvalidInput):
    """メッセージや添付ファイルが大きすぎる。"""


class UnsupportedAttachment(InvalidInput):
    """対応していない添付ファイル。"""


class RateLimited(DomainError):
    """短い時間に使いすぎている。"""


class FetchFailed(DomainError):
    """外部から求人票を取得できなかった。"""
