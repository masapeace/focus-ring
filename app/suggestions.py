# -*- coding: utf-8 -*-
"""
Focus Ring - 改善提案エンジン
ルールベース分析とLLM連携による行動改善アドバイス
"""

import os
from typing import List, Dict, Optional
from datetime import datetime

from .models import DailySummary, AIResponse
from .summarizer import calculate_daily_summary, get_category_distribution, get_time_of_day_productivity
from .db import get_filled_blocks_for_date, get_all_categories


# === ルールベース改善提案 ===

def generate_rule_based_suggestions(summary: DailySummary) -> AIResponse:
    """
    ルールベースの改善提案を生成
    
    Args:
        summary: 日次サマリデータ
        
    Returns:
        AIResponseオブジェクト
    """
    suggestions = []
    
    # 1. 妨害時間チェック（distract_ratio > 0.2）
    if summary.distract_ratio > 0.2:
        distract_pct = summary.distract_ratio * 100
        suggestions.append(
            f"⚠️ 妨害時間が {distract_pct:.1f}% と高めです。"
            f"動画・SNS時間を意識的に減らし、集中環境を整えましょう。"
        )
    
    # 2. 最低生産時間チェック（productive_blocks < 12 = 3時間）
    if summary.productive_blocks < 12:
        suggestions.append(
            f"📈 生産的な活動が {summary.productive_hours}時間でした。"
            f"最低3時間（12ブロック）を目標に、学習や作業時間を確保しましょう。"
        )
    
    # 3. 集中の連続性チェック（deep_streak_max < 4 = 1時間）
    if summary.deep_streak_max < 4:
        suggestions.append(
            f"🎯 最大連続集中時間が {summary.deep_streak_max * 15}分でした。"
            f"朝の2時間ブロックなど、長時間集中できる時間帯を作りましょう。"
        )
    
    # 4. カテゴリ切替が多い場合（context_switches 過多）
    expected_switches = max(summary.total_filled // 8, 1)
    if summary.context_switches > expected_switches * 2:
        suggestions.append(
            f"🔄 カテゴリ切替が {summary.context_switches}回と多めです。"
            f"同じ種類の作業をまとめて行うと効率が上がります。"
        )
    
    # 5. 入力不足チェック（total_filled < 40 = 半日）
    if summary.total_filled < 40:
        suggestions.append(
            f"📝 入力ブロックが {summary.total_filled}/80 です。"
            f"行動の記録を習慣化して、改善点を見つけやすくしましょう。"
        )
    
    # 6. 集中度平均チェック
    if summary.avg_focus_productive and summary.avg_focus_productive < 3.0:
        suggestions.append(
            f"💪 生産的活動の平均集中度が {summary.avg_focus_productive:.1f}/5.0 です。"
            f"環境を整えたり、タスクを細分化して集中度を上げていきましょう。"
        )
    
    # ポジティブな要素も含める
    positive_points = []
    
    if summary.productive_hours >= 3.0:
        positive_points.append(f"生産的時間 {summary.productive_hours}時間達成")
    
    if summary.deep_streak_max >= 6:  # 1.5時間以上
        positive_points.append(f"連続集中 {summary.deep_streak_max * 15}分達成")
    
    if summary.distract_ratio <= 0.1:
        positive_points.append("妨害時間を低く抑制")
    
    if summary.focus_score >= 10:
        positive_points.append(f"高フォーカススコア {summary.focus_score:.1f}")
    
    # 総括コメント生成
    summary_text = generate_summary_comment(summary, positive_points)
    
    # 提案が少ない場合は一般的なアドバイスを追加
    if len(suggestions) < 2:
        suggestions.extend([
            "🌅 朝の時間帯は集中力が高いので、重要なタスクに充てましょう。",
            "⏰ 15分タイマーを使って集中と休憩のリズムを作りましょう。",
            "📱 スマートフォンを別の部屋に置いて、誘惑を減らしましょう。"
        ])
    
    return AIResponse(
        suggestions=suggestions[:5],  # 最大5つまで
        summary=summary_text,
        is_ai_generated=False
    )


def generate_summary_comment(summary: DailySummary, positive_points: List[str]) -> str:
    """総括コメントを生成"""
    
    if summary.focus_score >= 15:
        level = "素晴らしい"
        emoji = "🎉"
    elif summary.focus_score >= 10:
        level = "良好"
        emoji = "👍"
    elif summary.focus_score >= 5:
        level = "普通"
        emoji = "📈"
    else:
        level = "要改善"
        emoji = "💪"
    
    base_comment = f"{emoji} 今日のフォーカススコアは {summary.focus_score:.1f} で{level}でした。"
    
    if positive_points:
        positive_text = "、".join(positive_points)
        base_comment += f" {positive_text}など、良い点もありました。"
    
    if summary.focus_score < 10:
        base_comment += " 明日はさらに集中できる環境を作って頑張りましょう！"
    else:
        base_comment += " この調子で継続していきましょう！"
    
    return base_comment


# === LLM連携改善提案 ===

def generate_ai_suggestions(date: str) -> AIResponse:
    """
    LLMを使用した詳細な改善提案を生成
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        AIResponseオブジェクト
    """
    # 環境変数からAPI キーを取得
    api_key = os.getenv('LLM_API_KEY')
    
    if not api_key:
        # API キーがない場合はルールベースにフォールバック
        summary = calculate_daily_summary(date)
        return generate_rule_based_suggestions(summary)
    
    try:
        # データ収集
        summary = calculate_daily_summary(date)
        category_dist = get_category_distribution(date)
        time_productivity = get_time_of_day_productivity(date)
        filled_blocks = get_filled_blocks_for_date(date)
        
        # LLM用のコンテキスト構築
        context = build_llm_context(date, summary, category_dist, time_productivity, filled_blocks)
        
        # LLM API呼び出し
        response = call_llm_api(context, api_key)
        
        return AIResponse(
            suggestions=response.get('suggestions', []),
            summary=response.get('summary', ''),
            is_ai_generated=True
        )
        
    except Exception as e:
        print(f"LLM API エラー: {e}")
        # エラー時はルールベースにフォールバック
        summary = calculate_daily_summary(date)
        fallback_response = generate_rule_based_suggestions(summary)
        fallback_response.summary += " (LLM接続エラーのためルールベース分析)"
        return fallback_response


def build_llm_context(date: str, summary: DailySummary, 
                     category_dist: Dict[str, Dict[str, float]], 
                     time_productivity: Dict[str, float],
                     filled_blocks: List) -> str:
    """LLM用のコンテキストデータを構築"""
    
    # カテゴリ情報取得
    categories = get_all_categories()
    category_info = {cat.code: f"{cat.label} (重み: {cat.weight})" for cat in categories}
    
    context = f"""
日付: {date}
フォーカススコア: {summary.focus_score:.1f} (生スコア: {summary.raw_score:.1f}, 連続集中: {summary.deep_streak_max}, 切替ペナルティ: {summary.penalty:.1f})

活動時間:
- 生産的: {summary.productive_hours}時間 ({summary.productive_blocks}ブロック)
- 妨害的: {summary.distract_hours}時間 ({summary.distract_blocks}ブロック)
- 中性: {summary.neutral_blocks}ブロック
- 妨害時間割合: {summary.distract_ratio * 100:.1f}%

集中度: 生産的活動の平均 {summary.avg_focus_productive or 'N/A'}/5.0

カテゴリ別時間分布:
"""
    
    for category, data in category_dist.items():
        category_name = category_info.get(category, category)
        context += f"- {category_name}: {data['hours']}時間 ({data['percentage']:.1f}%)\n"
    
    context += "\n時間帯別生産性:\n"
    for period, score in time_productivity.items():
        context += f"- {period}: {score:.1f}\n"
    
    context += f"""
カテゴリ切替回数: {summary.context_switches}回
入力済みブロック: {summary.total_filled}/80

この人の1日の行動パターンを分析し、生産性向上のための具体的な改善提案を3-5つ提供してください。
また、今日の総括コメントも含めてください。
"""
    
    return context


def call_llm_api(context: str, api_key: str) -> Dict:
    """LLM APIを呼び出し（OpenAI形式を想定）"""
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは生産性向上のコーチです。ユーザーの1日の行動データを分析し、具体的で実行可能な改善提案を日本語で提供してください。"
                },
                {
                    "role": "user", 
                    "content": context
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # レスポンスをパース（簡易的な実装）
        content = response.choices[0].message.content
        
        # 提案と総括を分離（簡易的な実装）
        lines = content.split('\n')
        suggestions = []
        summary = ""
        
        in_suggestions = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if '提案' in line or '改善' in line:
                in_suggestions = True
                continue
            elif '総括' in line or 'まとめ' in line:
                in_suggestions = False
                continue
            
            if in_suggestions and (line.startswith('-') or line.startswith('•') or line.startswith('1.')):
                suggestions.append(line.lstrip('-•1234567890. '))
            elif not in_suggestions:
                summary += line + " "
        
        return {
            'suggestions': suggestions[:5] if suggestions else ["LLMレスポンス解析エラー"],
            'summary': summary.strip() or "LLMレスポンス解析エラー"
        }
        
    except Exception as e:
        raise Exception(f"OpenAI API呼び出しエラー: {e}")


# === 公開API ===

def get_daily_suggestions(date: str) -> AIResponse:
    """
    指定日の改善提案を取得（LLM or ルールベース）
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        AIResponseオブジェクト
    """
    try:
        return generate_ai_suggestions(date)
    except Exception as e:
        print(f"提案生成エラー: {e}")
        # エラー時は基本的なルールベース提案
        summary = calculate_daily_summary(date)
        return generate_rule_based_suggestions(summary)


def get_quick_tips() -> List[str]:
    """一般的な生産性向上のクイックティップを取得"""
    return [
        "🌅 起床後の2時間は「ゴールデンタイム」。重要なタスクに充てましょう。",
        "📱 スマートフォンを別室に置いて、誘惑を物理的に遠ざけましょう。",
        "⏰ ポモドーロテクニック（25分集中→5分休憩）を試してみましょう。",
        "🧘 瞑想や深呼吸で集中力をリセットする習慣を作りましょう。",
        "📝 前日の夜に翌日のタスクリストを作成しておきましょう。",
        "💧 十分な水分補給で脳の働きを良好に保ちましょう。",
        "🚶 適度な運動で血流を改善し、集中力を高めましょう。",
        "🎵 集中できる音楽やホワイトノイズを活用しましょう。"
    ]


if __name__ == "__main__":
    # テスト実行
    from .utils import get_today
    
    print("=== Suggestions Test ===")
    
    today = get_today()
    print(f"今日の改善提案テスト: {today}")
    
    response = get_daily_suggestions(today)
    print(f"総括: {response.summary}")
    print("提案:")
    for i, suggestion in enumerate(response.suggestions, 1):
        print(f"  {i}. {suggestion}")
    print(f"AI生成: {response.is_ai_generated}")