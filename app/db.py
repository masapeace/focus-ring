# -*- coding: utf-8 -*-
"""
Focus Ring - データベース操作
SQLiteを使用した永続化層の実装
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from .models import DBBlock, DBCategory, INITIAL_CATEGORIES
from .utils import slot_index_to_time, validate_slot_index, validate_focus_level


# === データベース設定 ===

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "focus_ring.db")


# === データベース接続管理 ===

@contextmanager
def get_db_connection():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書ライクなアクセスを可能にする
    try:
        yield conn
    finally:
        conn.close()


# === データベース初期化 ===

def init_database():
    """
    データベースとテーブルを初期化
    
    初期化内容:
    - blocks テーブル作成
    - categories テーブル作成
    - 初期カテゴリデータ投入
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # blocks テーブル作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                slot_index INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                category TEXT,
                focus INTEGER,
                memo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, slot_index)
            )
        """)
        
        # categories テーブル作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                weight INTEGER NOT NULL,
                color TEXT NOT NULL,
                order_index INTEGER NOT NULL
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocks_date ON blocks(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocks_date_slot ON blocks(date, slot_index)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_order ON categories(order_index)")
        
        conn.commit()
        
        # 初期カテゴリデータ投入（存在しない場合のみ）
        insert_initial_categories()


def insert_initial_categories():
    """初期カテゴリデータを投入（存在チェック付き）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 既存カテゴリ数をチェック
        cursor.execute("SELECT COUNT(*) FROM categories")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"カテゴリは既に {existing_count} 件存在します。スキップします。")
            return
        
        # 初期カテゴリを一括投入
        for category in INITIAL_CATEGORIES:
            cursor.execute("""
                INSERT INTO categories (code, label, weight, color, order_index)
                VALUES (?, ?, ?, ?, ?)
            """, (category.code, category.label, category.weight, category.color, category.order_index))
        
        conn.commit()
        print(f"初期カテゴリ {len(INITIAL_CATEGORIES)} 件を投入しました。")


# === ブロック操作 ===

def get_day_blocks(date: str) -> List[DBBlock]:
    """
    指定日の全ブロック（80個）を取得
    未入力のスロットは category=None で返却
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        80個のDBBlockリスト（slot_index順）
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 既存ブロックを取得
        cursor.execute("""
            SELECT date, slot_index, start_time, category, focus, memo, created_at, updated_at
            FROM blocks
            WHERE date = ?
            ORDER BY slot_index
        """, (date,))
        
        existing_blocks = {}
        for row in cursor.fetchall():
            existing_blocks[row['slot_index']] = DBBlock(
                date=row['date'],
                slot_index=row['slot_index'],
                start_time=row['start_time'],
                category=row['category'],
                focus=row['focus'],
                memo=row['memo'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        
        # 80スロット全てを埋める（未入力は category=None）
        all_blocks = []
        for slot_index in range(80):
            if slot_index in existing_blocks:
                all_blocks.append(existing_blocks[slot_index])
            else:
                # 未入力スロット
                all_blocks.append(DBBlock(
                    date=date,
                    slot_index=slot_index,
                    start_time=slot_index_to_time(slot_index),
                    category=None,
                    focus=None,
                    memo=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ))
        
        return all_blocks


def upsert_block(date: str, slot_index: int, category: Optional[str] = None, 
                focus: Optional[int] = None, memo: Optional[str] = None) -> bool:
    """
    ブロックデータをUpsert（挿入/更新）
    
    Args:
        date: 日付 (YYYY-MM-DD)
        slot_index: スロット番号 (0-79)
        category: カテゴリコード
        focus: 集中度 (1-5)
        memo: メモ
        
    Returns:
        成功時True
    """
    # バリデーション
    if not validate_slot_index(slot_index):
        raise ValueError(f"無効なスロットインデックス: {slot_index}")
    
    if not validate_focus_level(focus):
        raise ValueError(f"無効な集中度: {focus}")
    
    start_time = slot_index_to_time(slot_index)
    now = datetime.now()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO blocks (date, slot_index, start_time, category, focus, memo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, slot_index) DO UPDATE SET
                category = excluded.category,
                focus = excluded.focus,
                memo = excluded.memo,
                updated_at = excluded.updated_at
        """, (date, slot_index, start_time, category, focus, memo, now, now))
        
        conn.commit()
        return True


def bulk_upsert_blocks(blocks_data: List[Dict[str, Any]]) -> int:
    """
    複数ブロックを一括Upsert
    
    Args:
        blocks_data: ブロックデータのリスト
        
    Returns:
        処理件数
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        
        processed = 0
        for block_data in blocks_data:
            date = block_data['date']
            slot_index = block_data['slot_index']
            category = block_data.get('category')
            focus = block_data.get('focus')
            memo = block_data.get('memo')
            
            # バリデーション
            if not validate_slot_index(slot_index):
                continue
            if not validate_focus_level(focus):
                continue
            
            start_time = slot_index_to_time(slot_index)
            
            cursor.execute("""
                INSERT INTO blocks (date, slot_index, start_time, category, focus, memo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, slot_index) DO UPDATE SET
                    category = excluded.category,
                    focus = excluded.focus,
                    memo = excluded.memo,
                    updated_at = excluded.updated_at
            """, (date, slot_index, start_time, category, focus, memo, now, now))
            
            processed += 1
        
        conn.commit()
        return processed


# === カテゴリ操作 ===

def get_all_categories() -> List[DBCategory]:
    """全カテゴリを順序付きで取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, label, weight, color, order_index
            FROM categories
            ORDER BY order_index
        """)
        
        categories = []
        for row in cursor.fetchall():
            categories.append(DBCategory(
                code=row['code'],
                label=row['label'],
                weight=row['weight'],
                color=row['color'],
                order_index=row['order_index']
            ))
        
        return categories


def get_category_by_code(code: str) -> Optional[DBCategory]:
    """コードでカテゴリを取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, label, weight, color, order_index
            FROM categories
            WHERE code = ?
        """, (code,))
        
        row = cursor.fetchone()
        if row:
            return DBCategory(
                code=row['code'],
                label=row['label'],
                weight=row['weight'],
                color=row['color'],
                order_index=row['order_index']
            )
        return None


def get_categories_weight_map() -> Dict[str, int]:
    """カテゴリコード -> 重みのマッピングを取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT code, weight FROM categories")
        return {row['code']: row['weight'] for row in cursor.fetchall()}


# === サマリ用データ取得 ===

def get_filled_blocks_for_date(date: str) -> List[Tuple[int, str, Optional[int]]]:
    """
    指定日の入力済みブロック情報を取得
    
    Args:
        date: 対象日 (YYYY-MM-DD)
        
    Returns:
        (slot_index, category, focus) のタプルリスト
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT slot_index, category, focus
            FROM blocks
            WHERE date = ? AND category IS NOT NULL
            ORDER BY slot_index
        """, (date,))
        
        return [(row['slot_index'], row['category'], row['focus']) 
                for row in cursor.fetchall()]


def get_date_range_summary_data(start_date: str, end_date: str) -> Dict[str, List[Tuple[int, str, Optional[int]]]]:
    """
    日付範囲の入力済みブロック情報を取得
    
    Args:
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        
    Returns:
        日付 -> [(slot_index, category, focus)] のマッピング
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, slot_index, category, focus
            FROM blocks
            WHERE date BETWEEN ? AND ? AND category IS NOT NULL
            ORDER BY date, slot_index
        """, (start_date, end_date))
        
        result = {}
        for row in cursor.fetchall():
            date = row['date']
            if date not in result:
                result[date] = []
            result[date].append((row['slot_index'], row['category'], row['focus']))
        
        return result


# === データベース管理 ===

def get_database_stats() -> Dict[str, Any]:
    """データベース統計情報を取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ブロック統計
        cursor.execute("SELECT COUNT(*) FROM blocks")
        total_blocks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM blocks WHERE category IS NOT NULL")
        filled_blocks = cursor.fetchone()[0]
        
        # 日付範囲
        cursor.execute("SELECT MIN(date), MAX(date) FROM blocks WHERE category IS NOT NULL")
        date_range = cursor.fetchone()
        
        # カテゴリ統計
        cursor.execute("SELECT COUNT(*) FROM categories")
        total_categories = cursor.fetchone()[0]
        
        return {
            'total_blocks': total_blocks,
            'filled_blocks': filled_blocks,
            'fill_rate': filled_blocks / max(total_blocks, 1),
            'date_range': {
                'start': date_range[0],
                'end': date_range[1]
            },
            'total_categories': total_categories,
            'db_path': DB_PATH
        }


def reset_database():
    """データベースを完全リセット（開発用）"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("データベースファイルを削除しました。")
    
    init_database()
    print("データベースを再初期化しました。")


if __name__ == "__main__":
    # テスト実行
    print("=== Database Test ===")
    
    # 初期化テスト
    init_database()
    
    # 統計情報表示
    stats = get_database_stats()
    print(f"データベース統計: {stats}")
    
    # カテゴリ表示
    categories = get_all_categories()
    print(f"カテゴリ数: {len(categories)}")
    for cat in categories[:3]:  # 最初の3件だけ表示
        print(f"  {cat.code}: {cat.label} (重み: {cat.weight})")