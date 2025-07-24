# -*- coding: utf-8 -*-
"""
Focus Ring - Vercel Serverless API
簡易版: すべてのロジックを1ファイルに統合
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os

# === データモデル ===

class CategoryModel(BaseModel):
    code: str
    label: str
    weight: int
    color: str
    order_index: int

class BlockResponse(BaseModel):
    date: str
    slot_index: int
    start_time: str
    category: Optional[str] = None
    focus: Optional[int] = None
    memo: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class BlockRequest(BaseModel):
    date: str
    slot_index: int
    category: Optional[str] = None
    focus: Optional[int] = None
    memo: Optional[str] = None

class DailySummary(BaseModel):
    date: str
    focus_score: float
    productive_blocks: int
    distract_blocks: int
    productive_hours: float
    distract_ratio: float
    deep_streak_max: int

class AIResponse(BaseModel):
    suggestions: List[str]
    summary: str
    is_ai_generated: bool

# === 固定データ ===

CATEGORIES = [
    {"code": "STUDY", "label": "📚 勉強", "weight": 3, "color": "#4CAF50", "order_index": 0},
    {"code": "ENGLISH", "label": "🌍 英語", "weight": 4, "color": "#2196F3", "order_index": 1},
    {"code": "AI_LEARNING", "label": "🤖 AI学習", "weight": 4, "color": "#9C27B0", "order_index": 2},
    {"code": "WORK_LOG", "label": "💼 作業ログ", "weight": 4, "color": "#FF9800", "order_index": 3},
    {"code": "BLOG", "label": "✍️ ブログ", "weight": 3, "color": "#795548", "order_index": 4},
    {"code": "WALK", "label": "🐕 散歩", "weight": 2, "color": "#8BC34A", "order_index": 5},
    {"code": "FARMING", "label": "🌱 農作業", "weight": 2, "color": "#4CAF50", "order_index": 6},
    {"code": "HOUSEWORK", "label": "🏠 家事", "weight": 1, "color": "#607D8B", "order_index": 7},
    {"code": "MANAGEMENT", "label": "📋 管理", "weight": 1, "color": "#9E9E9E", "order_index": 8},
    {"code": "HEALTH", "label": "💪 健康", "weight": 2, "color": "#F44336", "order_index": 9},
    {"code": "MEAL", "label": "🍽️ 食事", "weight": 0, "color": "#FFC107", "order_index": 10},
    {"code": "REST", "label": "😴 休憩", "weight": 0, "color": "#CDDC39", "order_index": 11},
    {"code": "SLEEP", "label": "🛏️ 睡眠", "weight": 0, "color": "#3F51B5", "order_index": 12},
    {"code": "VIDEO", "label": "📺 動画", "weight": -2, "color": "#E91E63", "order_index": 13},
    {"code": "SNS", "label": "📱 SNS", "weight": -3, "color": "#FF5722", "order_index": 14},
    {"code": "WASTE", "label": "❓ 無駄時間", "weight": -4, "color": "#424242", "order_index": 15}
]

# === メモリストレージ（簡易版） ===
memory_storage = {}

# === ユーティリティ関数 ===

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def validate_date_format(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def generate_time_blocks(date: str):
    """指定日の80ブロックを生成"""
    blocks = []
    start_time = datetime.strptime("04:00", "%H:%M")
    
    for i in range(80):
        time_slot = start_time + timedelta(minutes=15 * i)
        key = f"{date}_{i}"
        
        # メモリから既存データを取得
        existing_data = memory_storage.get(key, {})
        
        blocks.append(BlockResponse(
            date=date,
            slot_index=i,
            start_time=time_slot.strftime("%H:%M"),
            category=existing_data.get('category'),
            focus=existing_data.get('focus'),
            memo=existing_data.get('memo'),
            created_at=existing_data.get('created_at'),
            updated_at=existing_data.get('updated_at')
        ))
    
    return blocks

def calculate_simple_summary(date: str):
    """簡易サマリ計算"""
    blocks = generate_time_blocks(date)
    
    productive_blocks = sum(1 for b in blocks if b.category and get_category_weight(b.category) > 0)
    distract_blocks = sum(1 for b in blocks if b.category and get_category_weight(b.category) < 0)
    total_filled = sum(1 for b in blocks if b.category)
    
    focus_score = productive_blocks * 2 - distract_blocks
    productive_hours = productive_blocks * 0.25
    distract_ratio = (distract_blocks / max(total_filled, 1)) if total_filled > 0 else 0
    
    return DailySummary(
        date=date,
        focus_score=focus_score,
        productive_blocks=productive_blocks,
        distract_blocks=distract_blocks,
        productive_hours=productive_hours,
        distract_ratio=distract_ratio,
        deep_streak_max=4  # 固定値
    )

def get_category_weight(category_code: str):
    """カテゴリの重みを取得"""
    for cat in CATEGORIES:
        if cat["code"] == category_code:
            return cat["weight"]
    return 0

# === FastAPI アプリケーション ===

app = FastAPI(
    title="Focus Ring API",
    description="1日行動×集中タイムトラッカー",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === エンドポイント ===

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Focus Ring API"
    }

@app.post("/api/init")
async def initialize_database():
    return {
        "message": "データベースの初期化が完了しました",
        "stats": {"categories": len(CATEGORIES)}
    }

@app.get("/api/categories", response_model=List[CategoryModel])
async def get_categories():
    return [CategoryModel(**cat) for cat in CATEGORIES]

@app.get("/api/day/{date}", response_model=List[BlockResponse])
async def get_day_data(date: str):
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    return generate_time_blocks(date)

@app.post("/api/block")
async def update_block(request: BlockRequest):
    if not validate_date_format(request.date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    key = f"{request.date}_{request.slot_index}"
    memory_storage[key] = {
        'category': request.category,
        'focus': request.focus,
        'memo': request.memo,
        'updated_at': datetime.now().isoformat()
    }
    
    return {"message": "ブロックの更新が完了しました", "success": True}

@app.get("/api/summary/{date}", response_model=DailySummary)
async def get_daily_summary(date: str):
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    return calculate_simple_summary(date)

@app.get("/api/ai/suggestions/{date}", response_model=AIResponse)
async def get_ai_suggestions(date: str):
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    return AIResponse(
        suggestions=[
            "朝の時間を勉強に充てることをお勧めします",
            "休憩時間を適度に取って集中力を維持しましょう",
            "動画視聴時間を減らして生産的な活動を増やしましょう"
        ],
        summary="今日も記録を続けて、生産性を向上させましょう！",
        is_ai_generated=False
    )

@app.get("/api/stats")
async def get_system_stats():
    return {
        "database": {"total_categories": len(CATEGORIES)},
        "environment": {"current_date": get_today()},
        "api_version": "1.0.0"
    }

# Vercel用のハンドラー
handler = app