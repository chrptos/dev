"""チーム共通の観点テンプレートを登録する。

uv run python -m job_posting_agent.seed
uv run python -m job_posting_agent.seed --sample-job   # ローカル確認用の求人票 J-001 も入れる
"""

import argparse
import asyncio

from . import db, repository
from .db import JobPosting

TEAM_TEMPLATES = {
    "標準": (
        "求人票の必須スキルと歓迎スキルを整理し、候補者に合うかを判断するために"
        "確認すべきことを挙げる。求人票から分からない条件は、企業への確認事項にする。"
    ),
    "スピード重視": (
        "今日中にできる行動を最優先にする。候補者への打診、企業への確認、"
        "社内での共有のうち、すぐ着手できるものから順に並べる。"
    ),
}

SAMPLE_JOB = JobPosting(
    id="J-001",
    company="株式会社サンプル",
    title="バックエンドエンジニア",
    body=(
        "株式会社サンプル／バックエンドエンジニア（正社員）\n"
        "勤務地：東京都渋谷区（週2出社）\n"
        "給与：年収600万〜900万円\n"
        "必須：Go または Python での開発経験3年以上、PostgreSQL\n"
        "歓迎：Kubernetes、GCP\n"
        "募集背景：新規事業の立ち上げ\n"
    ),
)


async def main(sample_job: bool) -> None:
    for name, content in TEAM_TEMPLATES.items():
        await repository.save_team_template(name, content)
    print(f"チームのテンプレートを {len(TEAM_TEMPLATES)} 件登録しました")
    if sample_job:
        async with db.session() as s:
            await s.merge(SAMPLE_JOB)
            await s.commit()
        print("サンプルの求人票 J-001 を登録しました")
    engine = await db.get_engine()
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-job", action="store_true")
    asyncio.run(main(parser.parse_args().sample_job))
