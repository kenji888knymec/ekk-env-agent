"""
EKK環境管理課 マルチエージェント オーケストレーター
A〜Gの各エージェントを独立したAPIコールとして実行する
"""

import anthropic
import concurrent.futures

client = anthropic.Anthropic()

# ========== 各エージェントの指示 ==========

AGENTS = {
    "A_research": """
あなたはEKK環境管理課の調査専門エージェントです。
以下のテーマについて、法令・規格・通達・ガイドラインなど必要な情報を収集・整理してください。

調査の観点：
- 関連する法令・規格・通達の最新情報
- 省エネ法・フロン排出抑制法・廃棄物処理法・ISO14001・ISO50001への関連
- 環境省・経済産業省の告示・通達
- 出典・根拠条文・施行日を必ず明記する

テーマ：{theme}
""",

    "B_analysis": """
あなたはEKK環境管理課の分析専門エージェントです。
以下の調査結果を踏まえて、EKK・環境管理課への影響を具体的に分析してください。

分析の観点：
- EKKの現状業務への具体的な影響
- 対応が必要な事項と優先度
- 浅見副部長・吉田部長への報告に必要な情報
- 関係者（新井由紀・藤田彩子・見城祥太）への連絡事項

調査結果：{research}
""",

    "C_critic": """
あなたはEKK環境管理課の批判的分析専門エージェントです。
以下の分析結果の穴・見落とし・リスク・対応漏れを厳しく指摘してください。

指摘の観点：
- 法令対応で見落としている可能性があるもの
- リスクが過小評価されている箇所
- 対応期限や届出タイミングの見落とし
- EKK固有の事情で考慮すべき点

分析結果：{analysis}
""",

    "D_complement": """
あなたはEKK環境管理課の補完専門エージェントです。
批判係の指摘を踏まえて、不足している視点・観点・考慮事項を追加してください。

補完の観点：
- 誰も気づいていない論点を積極的に提示する
- NOKグループとの整合性
- CDP・TCFD・ESG開示への影響
- 内部監査・ISO審査での確認ポイント

批判係の指摘：{criticism}
""",

    "E_basis": """
あなたはEKK環境管理課の根拠調査専門エージェントです。
以下について根拠・経緯・背景を徹底的に調べてください。

調査内容：
- その基準・計算式はどこから来ているか（出典・法令・告示）
- なぜその算出方法が使われているか（制定の経緯・目的）
- 誰がその算出・届出を求めているか（省庁・機関・認証機関）
- どのような経緯でその制度が生まれたか（背景・歴史）

テーマ：{theme}
""",

    "F_checklist": """
あなたはEKK環境管理課の追加確認専門エージェントです。
作業完了前に「ついでに確認しておくべきこと」を提案してください。

確認の観点：
- 関連する他の法令・規格への影響はないか
- 期限や届出のタイミングで見落としはないか
- 浅見副部長・吉田部長への報告で必要な情報は揃っているか
- 次のアクションとして何を準備すべきか
- NOKカウンターパート（見城祥太）への連絡事項はないか

これまでの分析内容：{all_results}
""",

    "G_summary": """
あなたはEKK環境管理課のまとめ専門エージェントです。
A〜Fの全ての結果を統合して最終成果物を作成してください。

まとめの方針：
- 中村賢治が即座に行動できるレベルまで具体化する
- 成果物フォーマットは指示に応じてメール・報告書・Excel・PowerPointから選ぶ
- 法令対応は根拠条文・出典・施行日を必ず明記する
- 推測・不明点は「要確認」と明示する
- 浅見副部長・吉田部長への報告に使える形にまとめる

全エージェントの結果：{all_results}
"""
}


def run_agent(agent_name: str, prompt: str) -> str:
    """単一エージェントを実行する"""
    print(f"▶ {agent_name} 起動中...")
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.content[0].text
    print(f"✅ {agent_name} 完了")
    return result


def orchestrate(theme: str):
    """全エージェントをオーケストレートして最終結果を返す"""

    print(f"\nEKK環境管理課 マルチエージェント起動")
    print(f"テーマ：{theme}\n")

    # Phase 1：A（調査）とE（根拠調査）を並列実行
    print("Phase 1：A（調査）・E（根拠調査）並列実行中...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(run_agent, "A_research", AGENTS["A_research"].format(theme=theme))
        future_e = executor.submit(run_agent, "E_basis", AGENTS["E_basis"].format(theme=theme))
        research = future_a.result()
        basis = future_e.result()

    # Phase 2：B（分析）
    print("\nPhase 2：B（分析）実行中...")
    analysis = run_agent("B_analysis", AGENTS["B_analysis"].format(research=research))

    # Phase 3：C（批判）
    print("\nPhase 3：C（批判）実行中...")
    criticism = run_agent("C_critic", AGENTS["C_critic"].format(analysis=analysis))

    # Phase 4：D（補完）
    print("\nPhase 4：D（補完）実行中...")
    complement = run_agent("D_complement", AGENTS["D_complement"].format(criticism=criticism))

    # Phase 5：F（追加確認）
    print("\nPhase 5：F（追加確認）実行中...")
    all_so_far = f"調査：{research}\n根拠：{basis}\n分析：{analysis}\n批判：{criticism}\n補完：{complement}"
    checklist = run_agent("F_checklist", AGENTS["F_checklist"].format(all_results=all_so_far))

    # Phase 6：G（まとめ）
    print("\nPhase 6：G（まとめ）実行中...")
    all_results = f"{all_so_far}\n追加確認：{checklist}"
    final = run_agent("G_summary", AGENTS["G_summary"].format(all_results=all_results))

    print("\n✅ 全エージェント完了\n")
    print("="*60)
    print("【最終成果物】")
    print("="*60)
    print(final)

    return final


if __name__ == "__main__":
    theme = input("テーマ・依頼内容を入力してください：")
    orchestrate(theme)
