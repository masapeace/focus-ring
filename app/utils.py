# -*- coding: utf-8 -*-
"""
Focus Ring - ユーティリティ関数
時間変換・日付処理・共通機能
"""

from datetime import datetime, date, timedelta
from typing import Tuple, List, Optional


# === 時間変換ユーティリティ ===

def slot_index_to_time(slot_index: int) -> str:
    """
    スロットインデックスを時刻文字列に変換
    
    Args:
        slot_index: スロット番号 (0-79)
        
    Returns:
        時刻文字列 "HH:MM" 形式
        
    Examples:
        slot_index_to_time(0) -> "04:00"
        slot_index_to_time(1) -> "04:15"
        slot_index_to_time(79) -> "23:45"
    """
    if not 0 <= slot_index <= 79:
        raise ValueError(f"スロットインデックスは0-79の範囲で指定してください: {slot_index}")
    
    # 04:00 から開始、15分刻み
    start_hour = 4
    total_minutes = start_hour * 60 + slot_index * 15
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    return f"{hours:02d}:{minutes:02d}"


def time_to_slot_index(time_str: str) -> int:
    """
    時刻文字列をスロットインデックスに変換
    
    Args:
        time_str: 時刻文字列 "HH:MM" 形式
        
    Returns:
        スロット番号 (0-79)
        
    Examples:
        time_to_slot_index("04:00") -> 0
        time_to_slot_index("04:15") -> 1
        time_to_slot_index("23:45") -> 79
    """
    try:
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        raise ValueError(f"時刻形式が正しくありません: {time_str} (HH:MM形式で入力してください)")
    
    # 04:00 を基準とした総分数
    start_minutes = 4 * 60  # 04:00
    current_minutes = hour * 60 + minute
    
    if current_minutes < start_minutes:
        # 翌日扱い（00:00-03:59）
        current_minutes += 24 * 60
    
    slot_minutes = current_minutes - start_minutes
    slot_index = slot_minutes // 15
    
    if not 0 <= slot_index <= 79:
        raise ValueError(f"対応範囲外の時刻です: {time_str} (04:00-23:59)")
    
    return slot_index


def get_all_time_slots() -> List[Tuple[int, str]]:
    """
    全タイムスロットのリストを取得
    
    Returns:
        (slot_index, time_str) のタプルリスト
    """
    return [(i, slot_index_to_time(i)) for i in range(80)]


# === 日付ユーティリティ ===

def get_today() -> str:
    """今日の日付を YYYY-MM-DD 形式で取得"""
    return date.today().strftime('%Y-%m-%d')


def get_yesterday() -> str:
    """昨日の日付を YYYY-MM-DD 形式で取得"""
    return (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')


def get_tomorrow() -> str:
    """明日の日付を YYYY-MM-DD 形式で取得"""
    return (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')


def parse_date(date_str: str) -> date:
    """
    日付文字列をdateオブジェクトに変換
    
    Args:
        date_str: YYYY-MM-DD形式の日付文字列
        
    Returns:
        dateオブジェクト
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"日付形式が正しくありません: {date_str} (YYYY-MM-DD形式で入力してください)")


def format_date(date_obj: date) -> str:
    """dateオブジェクトを YYYY-MM-DD 形式の文字列に変換"""
    return date_obj.strftime('%Y-%m-%d')


def get_date_range(start_date: str, end_date: str) -> List[str]:
    """
    開始日から終了日までの日付リストを取得
    
    Args:
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        
    Returns:
        日付文字列のリスト
    """
    start = parse_date(start_date)
    end = parse_date(end_date)
    
    if start > end:
        raise ValueError(f"開始日が終了日より後です: {start_date} > {end_date}")
    
    dates = []
    current = start
    while current <= end:
        dates.append(format_date(current))
        current += timedelta(days=1)
    
    return dates


def get_week_dates(target_date: str) -> Tuple[str, str, List[str]]:
    """
    指定日を含む週の開始日、終了日、全日付を取得
    
    Args:
        target_date: 対象日 (YYYY-MM-DD)
        
    Returns:
        (開始日, 終了日, 日付リスト) のタプル
    """
    target = parse_date(target_date)
    
    # 月曜日を週の開始とする
    start_of_week = target - timedelta(days=target.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_str = format_date(start_of_week)
    end_str = format_date(end_of_week)
    week_dates = get_date_range(start_str, end_str)
    
    return start_str, end_str, week_dates


# === 文字列ユーティリティ ===

def truncate_text(text: str, max_length: int = 50) -> str:
    """
    テキストを指定長で切り詰め
    
    Args:
        text: 対象テキスト
        max_length: 最大文字数
        
    Returns:
        切り詰められたテキスト
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全な除算（ゼロ除算対策）
    
    Args:
        numerator: 分子
        denominator: 分母
        default: ゼロ除算時のデフォルト値
        
    Returns:
        除算結果またはデフォルト値
    """
    if denominator == 0:
        return default
    return numerator / denominator


# === バリデーションユーティリティ ===

def validate_slot_index(slot_index: int) -> bool:
    """スロットインデックスの妥当性チェック"""
    return 0 <= slot_index <= 79


def validate_focus_level(focus: Optional[int]) -> bool:
    """集中度の妥当性チェック"""
    if focus is None:
        return True
    return 1 <= focus <= 5


def validate_date_format(date_str: str) -> bool:
    """日付形式の妥当性チェック"""
    try:
        parse_date(date_str)
        return True
    except ValueError:
        return False


# === デバッグユーティリティ ===

def print_time_slot_table():
    """デバッグ用：全タイムスロットテーブルを出力"""
    print("=== Focus Ring タイムスロットテーブル ===")
    print("Index | Time  | Description")
    print("------|-------|------------")
    
    for slot_index, time_str in get_all_time_slots():
        description = ""
        if slot_index == 0:
            description = "起床"
        elif 0 <= slot_index <= 7:  # 04:00-05:45
            description = "朝活"
        elif 8 <= slot_index <= 15:  # 06:00-07:45
            description = "朝"
        elif 16 <= slot_index <= 31:  # 08:00-11:45
            description = "午前"
        elif 32 <= slot_index <= 47:  # 12:00-15:45
            description = "午後"
        elif 48 <= slot_index <= 63:  # 16:00-19:45
            description = "夕方"
        elif 64 <= slot_index <= 75:  # 20:00-22:45
            description = "夜"
        elif 76 <= slot_index <= 79:  # 23:00-23:45
            description = "就寝前"
        
        print(f"{slot_index:5d} | {time_str} | {description}")


if __name__ == "__main__":
    # テスト実行
    print("=== Utils Test ===")
    
    # 時間変換テスト
    print(f"slot 0 -> {slot_index_to_time(0)}")
    print(f"slot 79 -> {slot_index_to_time(79)}")
    print(f"04:00 -> slot {time_to_slot_index('04:00')}")
    print(f"23:45 -> slot {time_to_slot_index('23:45')}")
    
    # 日付テスト
    print(f"今日: {get_today()}")
    print(f"昨日: {get_yesterday()}")
    print(f"明日: {get_tomorrow()}")
    
    # タイムスロットテーブル出力
    # print_time_slot_table()