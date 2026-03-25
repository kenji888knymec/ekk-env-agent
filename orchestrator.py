"""
EKK環境管理課 マルチエージェント オーケストレーター
=========================================================
CLAUDE.md の設定に基づき、中村賢治さんの指示を受け取り
専門ドメイン層・共通機能層（A〜G）を並列・順次に動かして
最終成果物を生成するオーケストレーターです。

並列実行の設計:
  Phase 1 : [A] 調査係
  Phase 2 : [B] 分析係
  Phase 3 : [C] 批判係  ║  [E] 根拠調査係  （並列）
  Phase 4 : [D] 補完係  （C の出力を受けて）
  Phase 5 : [F] 追加確認係
  Phase 6 : [G] まとめ係
"""

import asyncio
import os
from datetime import date
from typing import Optional
import anthropic

# ── クライアント初期化 ─────────────────────────────────────────
client = anthropic.AsyncAnthropic()
MODEL = "claude-opus-4-6"
TODAY = date.today().isoformat()

# ── ドメイン判定マップ ─────────────────────────────────────────
DOMAIN_DESCRIPTIONS = {
    "法令チーム": "省エネ法・フロン排出抑制法・廃棄物処理法・環境省/経済産業省の告示・通達",
    "ISO/規格チーム": "ISO 14001・ISO 50001・審査対応・内部監査",
    "報告書チーム": "CDP・TCFD・ESGレポート・NOKグループ報告",
    "文書チーム": "社内メール・議事録・翻訳・PowerPoint・Excel",
}

SYSTEM_BASE = f"""あなたはイーグル工業（EKK）の環境管理課を支援するAIエージェントです。
ユーザーは中村賢治（環境管理課）です。
今日の日付: {TODAY}
主な関係者: 浅見副部長（直属上司）、吉田部長、新井由紀、藤田彩子、見城祥太（NOKカウンターパート）

重要ルール:
- 推測・不明点は「要確認」と明示し、絶対に推測で埋めない
- 法令対応は根拠条文・出典・施行日を必ず明記する
- 英語文書は和文・英文を並べて出す
- 修正は変更前・変更後を明示する
"""


# ── ヘルパー: 単一エージェント呼び出し ───────────────────────
async def call_agent(role: str, system_extra: str, prompt: str, max_tokens: int = 4096) -> str:
    """単一エージェントを呼び出し、テキスト応答を返す。"""
    response = await client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=SYSTEM_BASE + "\n\n" + system_extra,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    )


# ── ドメイン選択エージェント ──────────────────────────────────
async def select_domains(task: str) -> list[str]:
    """タスクを解析して必要なドメインチームを選択する。"""
    domain_list = "\n".join(f"- {k}: {v}" for k, v in DOMAIN_DESCRIPTIONS.items())
    prompt = f"""以下のタスクに必要なドメインチームを選んでください。
複数選択可。該当するチーム名のみをカンマ区切りで返してください（説明不要）。

選択肢:
{domain_list}

タスク:
{task}"""

    result = await call_agent(
        role="オーケストレーター",
        system_extra="あなたはタスクを分析してドメインチームを選ぶオーケストレーターです。",
        prompt=prompt,
        max_tokens=256,
    )
    selected = []
    for domain in DOMAIN_DESCRIPTIONS:
        if domain in result:
            selected.append(domain)
    return selected if selected else list(DOMAIN_DESCRIPTIONS.keys())


# ── Phase 1: A 調査係 ─────────────────────────────────────────
async def agent_a(task: str, domains: list[str]) -> str:
    domain_str = "・".join(domains)
    return await call_agent(
        role="A調査係",
        system_extra=f"あなたは【A：調査係】です。担当ドメイン: {domain_str}\n法令・規格・通達・ガイドラインなど必要な情報を収集・整理してください。",
        prompt=f"以下のタスクに関して必要な情報を収集・整理してください。\n\n【タスク】\n{task}",
        max_tokens=3000,
    )


# ── Phase 2: B 分析係 ─────────────────────────────────────────
async def agent_b(task: str, result_a: str) -> str:
    return await call_agent(
        role="B分析係",
        system_extra="あなたは【B：分析係】です。調査係の情報がEKK・環境管理課に与える影響を具体的に分析してください。",
        prompt=f"【タスク】\n{task}\n\n【A調査係の結果】\n{result_a}\n\n上記を踏まえ、EKK・環境管理課への影響を具体的に分析してください。",
        max_tokens=3000,
    )


# ── Phase 3: C 批判係（E と並列） ─────────────────────────────
async def agent_c(task: str, result_a: str, result_b: str) -> str:
    return await call_agent(
        role="C批判係",
        system_extra="あなたは【C：批判係】です。分析結果の穴・見落とし・リスク・対応漏れを厳しく指摘してください。",
        prompt=f"【タスク】\n{task}\n\n【A調査係】\n{result_a}\n\n【B分析係】\n{result_b}\n\n上記の分析の穴・見落とし・リスク・対応漏れを厳しく指摘してください。",
        max_tokens=2500,
    )


async def agent_e(task: str, result_a: str, result_b: str) -> str:
    return await call_agent(
        role="E根拠調査係",
        system_extra=(
            "あなたは【E：根拠調査係】です。以下を必ず調べて明記してください:\n"
            "- その基準・計算式はどこから来ているか（出典・法令・告示）\n"
            "- なぜその算出方法が使われているか（制定の経緯・目的）\n"
            "- 誰がその算出・届出を求めているか（省庁・機関・認証機関）\n"
            "- どのような経緯でその制度が生まれたか（背景・歴史）"
        ),
        prompt=f"【タスク】\n{task}\n\n【A調査係】\n{result_a}\n\n【B分析係】\n{result_b}\n\n関連する法令・基準・制度の根拠と背景を調査してください。",
        max_tokens=2500,
    )


# ── Phase 4: D 補完係 ─────────────────────────────────────────
async def agent_d(task: str, result_b: str, result_c: str) -> str:
    return await call_agent(
        role="D補完係",
        system_extra="あなたは【D：補完係】です。批判係の指摘を踏まえて不足している視点・観点・考慮事項を追加し、誰も気づいていない論点を積極的に提示してください。",
        prompt=f"【タスク】\n{task}\n\n【B分析係】\n{result_b}\n\n【C批判係の指摘】\n{result_c}\n\n不足している視点・考慮事項を補完してください。誰も気づいていない論点も提示してください。",
        max_tokens=2500,
    )


# ── Phase 5: F 追加確認係 ─────────────────────────────────────
async def agent_f(task: str, result_b: str, result_c: str, result_d: str, result_e: str) -> str:
    return await call_agent(
        role="F追加確認係",
        system_extra=(
            "あなたは【F：追加確認係】です。作業が終わる前に「ついでに確認しておくべきこと」を提案してください:\n"
            "- 関連する他の法令・規格への影響はないか\n"
            "- 期限や届出のタイミングで見落としはないか\n"
            "- 浅見副部長・吉田部長への報告で必要な情報は揃っているか\n"
            "- 次のアクションとして何を準備すべきか"
        ),
        prompt=(
            f"【タスク】\n{task}\n\n"
            f"【B分析係】\n{result_b}\n\n"
            f"【C批判係】\n{result_c}\n\n"
            f"【D補完係】\n{result_d}\n\n"
            f"【E根拠調査係】\n{result_e}\n\n"
            "追加で確認しておくべきことを提案してください。"
        ),
        max_tokens=2000,
    )


# ── Phase 6: G まとめ係 ───────────────────────────────────────
async def agent_g(
    task: str,
    domains: list[str],
    result_a: str,
    result_b: str,
    result_c: str,
    result_d: str,
    result_e: str,
    result_f: str,
    output_format: str = "報告書",
) -> str:
    return await call_agent(
        role="Gまとめ係",
        system_extra=(
            f"あなたは【G：まとめ係】です。A〜Fの全ての結果を統合して最終成果物を作成してください。\n"
            f"出力フォーマット: {output_format}\n"
            f"担当ドメイン: {'・'.join(domains)}"
        ),
        prompt=(
            f"【タスク】\n{task}\n\n"
            f"【A調査係】\n{result_a}\n\n"
            f"【B分析係】\n{result_b}\n\n"
            f"【C批判係】\n{result_c}\n\n"
            f"【D補完係】\n{result_d}\n\n"
            f"【E根拠調査係】\n{result_e}\n\n"
            f"【F追加確認係】\n{result_f}\n\n"
            f"上記全ての内容を統合して、中村賢治さんへの最終成果物（{output_format}形式）を作成してください。\n"
            "見やすく構造化し、浅見副部長・吉田部長への報告にも使えるレベルで仕上げてください。"
        ),
        max_tokens=6000,
    )


# ── メイン オーケストレーター ──────────────────────────────────
async def orchestrate(task: str, output_format: str = "報告書") -> dict:
    """
    タスクを受け取り、全エージェントを順次・並列で実行して最終成果物を返す。

    Args:
        task: 中村さんからの指示
        output_format: 成果物フォーマット（報告書/メール/Excel/PowerPoint）

    Returns:
        各エージェントの出力と最終成果物を含む辞書
    """
    print(f"\n{'='*60}")
    print("EKK環境管理課 マルチエージェント オーケストレーター")
    print(f"{'='*60}")
    print(f"タスク: {task[:80]}{'...' if len(task) > 80 else ''}")
    print(f"出力形式: {output_format}\n")

    # ── ドメイン選択 ──────────────────────────────────────────
    print("▶ ドメイン選択中...")
    domains = await select_domains(task)
    print(f"  選択されたドメイン: {', '.join(domains)}")

    # ── Phase 1: A 調査係 ─────────────────────────────────────
    print("\n▶ [A] 調査係 実行中...")
    result_a = await agent_a(task, domains)
    print("  完了 ✓")

    # ── Phase 2: B 分析係 ─────────────────────────────────────
    print("\n▶ [B] 分析係 実行中...")
    result_b = await agent_b(task, result_a)
    print("  完了 ✓")

    # ── Phase 3: C と E を並列実行 ────────────────────────────
    print("\n▶ [C] 批判係 + [E] 根拠調査係 並列実行中...")
    result_c, result_e = await asyncio.gather(
        agent_c(task, result_a, result_b),
        agent_e(task, result_a, result_b),
    )
    print("  C批判係 完了 ✓")
    print("  E根拠調査係 完了 ✓")

    # ── Phase 4: D 補完係 ─────────────────────────────────────
    print("\n▶ [D] 補完係 実行中...")
    result_d = await agent_d(task, result_b, result_c)
    print("  完了 ✓")

    # ── Phase 5: F 追加確認係 ─────────────────────────────────
    print("\n▶ [F] 追加確認係 実行中...")
    result_f = await agent_f(task, result_b, result_c, result_d, result_e)
    print("  完了 ✓")

    # ── Phase 6: G まとめ係 ───────────────────────────────────
    print("\n▶ [G] まとめ係 実行中（最終成果物生成）...")
    result_g = await agent_g(
        task, domains, result_a, result_b, result_c, result_d, result_e, result_f,
        output_format=output_format,
    )
    print("  完了 ✓")

    print(f"\n{'='*60}")
    print("全エージェント完了 — 最終成果物を生成しました。")
    print(f"{'='*60}\n")

    return {
        "task": task,
        "domains": domains,
        "output_format": output_format,
        "agents": {
            "A_調査": result_a,
            "B_分析": result_b,
            "C_批判": result_c,
            "D_補完": result_d,
            "E_根拠調査": result_e,
            "F_追加確認": result_f,
            "G_まとめ（最終成果物）": result_g,
        },
        "final_output": result_g,
    }


# ── CLI エントリーポイント ─────────────────────────────────────
async def main():
    import sys

    if len(sys.argv) < 2:
        # デモ用サンプルタスク
        task = (
            "EKKとNOKの統合（26年10月予定）に向けて、環境管理課として"
            "事前に準備しておくべき法令・許認可関係の対応事項をまとめてください。"
        )
        output_format = "報告書"
    else:
        task = sys.argv[1]
        output_format = sys.argv[2] if len(sys.argv) > 2 else "報告書"

    result = await orchestrate(task, output_format=output_format)

    # 最終成果物を表示
    print("\n" + "="*60)
    print("【最終成果物】")
    print("="*60)
    print(result["final_output"])

    # 詳細ログをファイルに保存（任意）
    import json
    log_path = "orchestrator_output.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n（詳細ログを {log_path} に保存しました）")


if __name__ == "__main__":
    asyncio.run(main())
