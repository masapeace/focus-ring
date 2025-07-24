# -*- coding: utf-8 -*-
"""
Focus Ring - フォーカススコア計算とサマリ機能
1日の行動データから総合的な集中度指標を算出
"""

from typing import List, Tuple, Dict, Optional
from collections import defaultdict

from .models import DailySummary, TrendDataPoint, TrendResponse
from .db import get_filled_blocks_for_date, get_categories_weight_map, get_date_range_summary_data
from .utils import safe_divide


# === フォーカススコア計算 ===

def calculate_daily_summary(date: str) -> DailySummary:
    """
    指定日の詳細サマリを計算
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        DailySummaryオブジェクト
    """
    # データ取得
    filled_blocks = get_filled_blocks_for_date(date)
    weight_map = get_categories_weight_map()
    
    if not filled_blocks:
        # 未入力の場合はゼロサマリを返す
        return DailySummary(
            date=date,
            focus_score=0.0,
            raw_score=0.0,
            deep_streak_max=0,
            context_switches=0,
            penalty=0.0,
            productive_blocks=0,
            distract_blocks=0,
            neutral_blocks=0,
            total_filled=0,
            productive_hours=0.0,
            distract_hours=0.0,
            distract_ratio=0.0,
            avg_focus_productive=None
        )
    
    # 基本指標計算
    total_filled = len(filled_blocks)
    raw_score = 0.0
    productive_blocks = 0
    distract_blocks = 0
    neutral_blocks = 0
    focus_sum_productive = 0.0
    focus_count_productive = 0
    
    categories = []  # カテゴリ遷移追跡用
    
    for slot_index, category, focus in filled_blocks:
        weight = weight_map.get(category, 0)
        raw_score += weight
        categories.append(category)
        
        if weight > 0:
            productive_blocks += 1
            if focus is not None:
                focus_sum_productive += focus
                focus_count_productive += 1
        elif weight < 0:
            distract_blocks += 1
        else:
            neutral_blocks += 1
    
    # 深い集中ストリーク計算
    deep_streak_max = calculate_deep_streak_max(filled_blocks, weight_map)
    
    # カテゴリ切替回数計算
    context_switches = calculate_context_switches(categories)
    
    # ペナルティ計算
    penalty = max(0, context_switches - total_filled / 8) * 0.5
    
    # 最終フォーカススコア
    focus_score = raw_score + deep_streak_max - penalty
    
    # 時間計算（15分 = 0.25時間）
    productive_hours = productive_blocks * 0.25
    distract_hours = distract_blocks * 0.25
    
    # 妨害時間割合
    total_active_blocks = productive_blocks + distract_blocks
    distract_ratio = safe_divide(distract_blocks, total_active_blocks, 0.0)
    
    # 平均集中度（生産的ブロックのみ）
    avg_focus_productive = None
    if focus_count_productive > 0:
        avg_focus_productive = focus_sum_productive / focus_count_productive
    
    return DailySummary(
        date=date,
        focus_score=round(focus_score, 2),
        raw_score=round(raw_score, 2),
        deep_streak_max=deep_streak_max,
        context_switches=context_switches,
        penalty=round(penalty, 2),
        productive_blocks=productive_blocks,
        distract_blocks=distract_blocks,
        neutral_blocks=neutral_blocks,
        total_filled=total_filled,
        productive_hours=round(productive_hours, 2),
        distract_hours=round(distract_hours, 2),
        distract_ratio=round(distract_ratio, 3),
        avg_focus_productive=round(avg_focus_productive, 2) if avg_focus_productive else None
    )


def calculate_deep_streak_max(filled_blocks: List[Tuple[int, str, Optional[int]]], 
                            weight_map: Dict[str, int]) -> int:
    """
    最大連続生産的ブロック数を計算
    
    Args:
        filled_blocks: (slot_index, category, focus) のリスト
        weight_map: カテゴリ -> 重みのマッピング
        
    Returns:
        最大連続ブロック数
    """
    if not filled_blocks:
        return 0
    
    max_streak = 0
    current_streak = 0
    last_slot = -1
    
    for slot_index, category, focus in filled_blocks:
        weight = weight_map.get(category, 0)
        
        if weight > 0:  # 生産的カテゴリ
            if last_slot == -1 or slot_index == last_slot + 1:
                # 連続している
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                # 連続が途切れた
                current_streak = 1
        else:
            # 非生産的カテゴリで連続リセット
            current_streak = 0
        
        last_slot = slot_index
    
    return max_streak


def calculate_context_switches(categories: List[str]) -> int:
    """
    カテゴリ切替回数を計算
    
    Args:
        categories: カテゴリのリスト（時系列順）
        
    Returns:
        切替回数
    """
    if len(categories) <= 1:
        return 0
    
    switches = 0
    for i in range(1, len(categories)):
        if categories[i] != categories[i-1]:
            switches += 1
    
    return switches


# === 推移データ計算 ===

def calculate_trend_data(start_date: str, end_date: str) -> TrendResponse:
    """
    期間内の推移データを計算
    
    Args:
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        
    Returns:
        TrendResponseオブジェクト
    """
    # 期間内の全データを取得
    date_blocks_map = get_date_range_summary_data(start_date, end_date)
    weight_map = get_categories_weight_map()
    
    trend_data = []
    total_score = 0.0
    total_productive = 0.0
    valid_days = 0
    
    # 各日のサマリを計算
    for date, blocks in date_blocks_map.items():
        if not blocks:
            continue
        
        # 簡易サマリ計算（計算量削減のため）
        raw_score = sum(weight_map.get(category, 0) for _, category, _ in blocks)
        deep_streak = calculate_deep_streak_max(blocks, weight_map)
        context_switches = calculate_context_switches([cat for _, cat, _ in blocks])
        penalty = max(0, context_switches - len(blocks) / 8) * 0.5
        focus_score = raw_score + deep_streak - penalty
        
        productive_blocks = sum(1 for _, cat, _ in blocks if weight_map.get(cat, 0) > 0)
        distract_blocks = sum(1 for _, cat, _ in blocks if weight_map.get(cat, 0) < 0)
        
        productive_hours = productive_blocks * 0.25
        distract_hours = distract_blocks * 0.25
        
        trend_data.append(TrendDataPoint(
            date=date,
            focus_score=round(focus_score, 2),
            productive_hours=round(productive_hours, 2),
            distract_hours=round(distract_hours, 2)
        ))
        
        total_score += focus_score
        total_productive += productive_hours
        valid_days += 1
    
    # 期間平均計算
    period_avg_score = safe_divide(total_score, valid_days, 0.0)
    period_avg_productive = safe_divide(total_productive, valid_days, 0.0)
    
    # 日付順にソート
    trend_data.sort(key=lambda x: x.date)
    
    return TrendResponse(
        trend_data=trend_data,
        period_avg_score=round(period_avg_score, 2),
        period_avg_productive=round(period_avg_productive, 2)
    )


# === 推移分析ユーティリティ ===

def get_category_distribution(date: str) -> Dict[str, Dict[str, float]]:
    """
    指定日のカテゴリ別時間分布を取得
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        カテゴリ -> {hours, blocks, percentage} のマッピング
    """
    filled_blocks = get_filled_blocks_for_date(date)
    
    if not filled_blocks:
        return {}
    
    category_counts = defaultdict(int)
    for _, category, _ in filled_blocks:
        category_counts[category] += 1
    
    total_blocks = len(filled_blocks)
    result = {}
    
    for category, blocks in category_counts.items():
        hours = blocks * 0.25
        percentage = (blocks / total_blocks) * 100
        
        result[category] = {
            'hours': round(hours, 2),
            'blocks': blocks,
            'percentage': round(percentage, 1)
        }
    
    return result


def get_time_of_day_productivity(date: str) -> Dict[str, float]:
    """
    時間帯別生産性を計算
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        時間帯 -> 生産性スコアのマッピング
    """
    filled_blocks = get_filled_blocks_for_date(date)
    weight_map = get_categories_weight_map()
    
    if not filled_blocks:
        return {}
    
    # 時間帯定義（4時間単位）
    time_periods = {
        '早朝 (04:00-07:59)': (0, 15),    # slot 0-15
        '午前 (08:00-11:59)': (16, 31),   # slot 16-31
        '午後 (12:00-15:59)': (32, 47),   # slot 32-47
        '夕方 (16:00-19:59)': (48, 63),   # slot 48-63
        '夜 (20:00-23:59)': (64, 79),     # slot 64-79
    }
    
    period_scores = {}
    
    for period_name, (start_slot, end_slot) in time_periods.items():
        period_blocks = [
            (slot, category, focus) for slot, category, focus in filled_blocks
            if start_slot <= slot <= end_slot
        ]
        
        if not period_blocks:
            period_scores[period_name] = 0.0
            continue
        
        # 期間内の平均重み
        total_weight = sum(weight_map.get(category, 0) for _, category, _ in period_blocks)
        avg_weight = total_weight / len(period_blocks)
        period_scores[period_name] = round(avg_weight, 2)
    
    return period_scores


def get_focus_level_distribution(date: str) -> Dict[int, int]:
    """
    集中度レベル別の分布を取得
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        集中度 -> ブロック数のマッピング
    """
    filled_blocks = get_filled_blocks_for_date(date)
    
    focus_counts = defaultdict(int)
    for _, _, focus in filled_blocks:
        if focus is not None:
            focus_counts[focus] += 1
    
    return dict(focus_counts)


if __name__ == "__main__":
    # テスト実行
    from .utils import get_today
    
    print("=== Summarizer Test ===")
    
    today = get_today()
    print(f"今日のサマリ計算テスト: {today}")
    
    summary = calculate_daily_summary(today)
    print(f"フォーカススコア: {summary.focus_score}")
    print(f"生産的時間: {summary.productive_hours}時間")
    print(f"妨害時間割合: {summary.distract_ratio * 100:.1f}%")