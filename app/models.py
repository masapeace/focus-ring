# -*- coding: utf-8 -*-
"""
Focus Ring - Pydanticモデル定義
1日行動×集中タイムトラッカーのAPIリクエスト/レスポンス型定義
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# === APIリクエスト/レスポンスモデル ===

class BlockRequest(BaseModel):
    """ブロック更新リクエストモデル"""
    date: str = Field(..., description="日付 (YYYY-MM-DD)")
    slot_index: int = Field(..., ge=0, le=79, description="スロットインデックス (0-79)")
    category: Optional[str] = Field(None, description="カテゴリコード")
    focus: Optional[int] = Field(None, ge=1, le=5, description="集中度 (1-5)")
    memo: Optional[str] = Field(None, max_length=200, description="メモ")


class BlockResponse(BaseModel):
    """ブロック情報レスポンスモデル"""
    date: str
    slot_index: int
    start_time: str  # "04:00", "04:15" 形式
    category: Optional[str]
    focus: Optional[int]
    memo: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class BulkBlockRequest(BaseModel):
    """複数ブロック一括更新リクエストモデル"""
    blocks: List[BlockRequest] = Field(..., description="ブロックリスト")


class CategoryModel(BaseModel):
    """カテゴリモデル"""
    code: str = Field(..., description="カテゴリコード (例: STUDY, ENGLISH)")
    label: str = Field(..., description="表示ラベル")
    weight: int = Field(..., description="フォーカス重み (-4 to +4)")
    color: str = Field(..., description="CSSクラス名")
    order_index: int = Field(..., description="表示順序")


class DailySummary(BaseModel):
    """日次サマリモデル"""
    date: str
    focus_score: float = Field(..., description="総合フォーカススコア")
    raw_score: float = Field(..., description="重み合計の生スコア")
    deep_streak_max: int = Field(..., description="最大連続集中ブロック数")
    context_switches: int = Field(..., description="カテゴリ切替回数")
    penalty: float = Field(..., description="切替ペナルティ")
    
    productive_blocks: int = Field(..., description="生産的ブロック数 (weight > 0)")
    distract_blocks: int = Field(..., description="妨害ブロック数 (weight < 0)")
    neutral_blocks: int = Field(..., description="中性ブロック数 (weight = 0)")
    total_filled: int = Field(..., description="入力済み総ブロック数")
    
    productive_hours: float = Field(..., description="生産的時間 (時)")
    distract_hours: float = Field(..., description="妨害時間 (時)")
    distract_ratio: float = Field(..., description="妨害時間割合")
    avg_focus_productive: Optional[float] = Field(None, description="生産的ブロックの平均集中度")


class TrendDataPoint(BaseModel):
    """推移データポイント"""
    date: str
    focus_score: float
    productive_hours: float
    distract_hours: float


class TrendResponse(BaseModel):
    """推移データレスポンス"""
    trend_data: List[TrendDataPoint]
    period_avg_score: float = Field(..., description="期間平均フォーカススコア")
    period_avg_productive: float = Field(..., description="期間平均生産的時間")


class AIResponse(BaseModel):
    """AI提案レスポンス"""
    suggestions: List[str] = Field(..., description="改善提案リスト")
    summary: str = Field(..., description="総括コメント")
    is_ai_generated: bool = Field(..., description="AI生成かルールベースか")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str = Field(..., description="エラーメッセージ")


# === 内部データモデル ===

class DBBlock(BaseModel):
    """データベースブロック（内部用）"""
    id: Optional[int] = None
    date: str
    slot_index: int
    start_time: str
    category: Optional[str]
    focus: Optional[int]
    memo: Optional[str]
    created_at: datetime
    updated_at: datetime


class DBCategory(BaseModel):
    """データベースカテゴリ（内部用）"""
    id: Optional[int] = None
    code: str
    label: str
    weight: int
    color: str
    order_index: int


# === 初期カテゴリ定義 ===
INITIAL_CATEGORIES = [
    # 高生産性（重み +3 ~ +4）
    CategoryModel(code="STUDY", label="📚 勉強", weight=3, color="category-study", order_index=1),
    CategoryModel(code="ENGLISH", label="🌍 英語", weight=4, color="category-english", order_index=2),
    CategoryModel(code="AI", label="🤖 AI学習", weight=4, color="category-ai", order_index=3),
    CategoryModel(code="WORK_LOG", label="💼 作業ログ", weight=4, color="category-work", order_index=4),
    CategoryModel(code="BLOG", label="✍️ ブログ", weight=3, color="category-blog", order_index=5),
    
    # 中生産性（重み +1 ~ +2）
    CategoryModel(code="PET_WALK", label="🐕 散歩", weight=2, color="category-pet", order_index=6),
    CategoryModel(code="FARM", label="🌱 農作業", weight=2, color="category-farm", order_index=7),
    CategoryModel(code="HOUSE", label="🏠 家事", weight=1, color="category-house", order_index=8),
    CategoryModel(code="ADMIN", label="📋 管理", weight=1, color="category-admin", order_index=9),
    CategoryModel(code="HEALTH", label="💪 健康", weight=2, color="category-health", order_index=10),
    
    # 中性（重み 0）
    CategoryModel(code="EAT", label="🍽️ 食事", weight=0, color="category-eat", order_index=11),
    CategoryModel(code="REST", label="😴 休憩", weight=0, color="category-rest", order_index=12),
    CategoryModel(code="SLEEP", label="🛏️ 睡眠", weight=0, color="category-sleep", order_index=13),
    
    # 妨害系（重み -2 ~ -4）
    CategoryModel(code="VIDEO", label="📺 動画", weight=-2, color="category-video", order_index=14),
    CategoryModel(code="SNS", label="📱 SNS", weight=-3, color="category-sns", order_index=15),
    CategoryModel(code="LOST", label="❓ 無駄時間", weight=-4, color="category-lost", order_index=16),
]