# -*- coding: utf-8 -*-
"""
Focus Ring - FastAPI メインアプリケーション
1日行動×集中タイムトラッカーのAPIサーバー
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional, List
from datetime import datetime

from .models import (
    BlockRequest, BlockResponse, BulkBlockRequest, CategoryModel, 
    DailySummary, TrendResponse, AIResponse, ErrorResponse
)
from .db import (
    init_database, get_day_blocks, upsert_block, bulk_upsert_blocks, 
    get_all_categories, get_database_stats
)
from .summarizer import calculate_daily_summary, calculate_trend_data
from .suggestions import get_daily_suggestions
from .utils import get_today, validate_date_format, get_date_range


# === FastAPI アプリケーション初期化 ===

app = FastAPI(
    title="Focus Ring API",
    description="1日行動×集中タイムトラッカー",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なドメインに制限
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル提供設定
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# === エラーハンドリング ===

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """グローバル例外ハンドラー"""
    return JSONResponse(
        status_code=500,
        content={"error": f"内部サーバーエラー: {str(exc)}"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP例外ハンドラー"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


# === ルートエンドポイント ===

@app.get("/")
async def root():
    """ルートページ - index.htmlを返す"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Focus Ring API Server", "status": "running"}


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Focus Ring API"
    }


# === データベース初期化エンドポイント ===

@app.post("/api/init")
async def initialize_database():
    """
    データベースとカテゴリを初期化
    既存データがある場合はスキップ
    """
    try:
        init_database()
        stats = get_database_stats()
        
        return {
            "message": "データベースの初期化が完了しました",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初期化エラー: {str(e)}")


# === ブロック操作エンドポイント ===

@app.get("/api/day/{date}", response_model=List[BlockResponse])
async def get_day_data(date: str):
    """
    指定日の全ブロック（80個）を取得
    未入力のブロックは category=null で返却
    """
    # 日付バリデーション
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    try:
        blocks = get_day_blocks(date)
        
        # DBBlockをBlockResponseに変換
        response_blocks = []
        for block in blocks:
            response_blocks.append(BlockResponse(
                date=block.date,
                slot_index=block.slot_index,
                start_time=block.start_time,
                category=block.category,
                focus=block.focus,
                memo=block.memo,
                created_at=block.created_at,
                updated_at=block.updated_at
            ))
        
        return response_blocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データ取得エラー: {str(e)}")


@app.post("/api/block")
async def update_block(request: BlockRequest):
    """単一ブロックをUpsert（挿入/更新）"""
    # 日付バリデーション
    if not validate_date_format(request.date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    try:
        success = upsert_block(
            date=request.date,
            slot_index=request.slot_index,
            category=request.category,
            focus=request.focus,
            memo=request.memo
        )
        
        if success:
            return {"message": "ブロックの更新が完了しました", "success": True}
        else:
            raise HTTPException(status_code=500, detail="ブロック更新に失敗しました")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新エラー: {str(e)}")


@app.post("/api/bulk")
async def bulk_update_blocks(request: BulkBlockRequest):
    """複数ブロックを一括更新"""
    if not request.blocks:
        raise HTTPException(status_code=400, detail="更新するブロックが指定されていません")
    
    try:
        # リクエストデータを辞書リストに変換
        blocks_data = []
        for block in request.blocks:
            if not validate_date_format(block.date):
                raise HTTPException(status_code=400, detail=f"日付形式が正しくありません: {block.date}")
            
            blocks_data.append({
                'date': block.date,
                'slot_index': block.slot_index,
                'category': block.category,
                'focus': block.focus,
                'memo': block.memo
            })
        
        processed_count = bulk_upsert_blocks(blocks_data)
        
        return {
            "message": f"{processed_count} 件のブロックを更新しました",
            "processed": processed_count,
            "requested": len(request.blocks)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括更新エラー: {str(e)}")


# === サマリエンドポイント ===

@app.get("/api/summary/{date}", response_model=DailySummary)
async def get_daily_summary(date: str):
    """指定日のフォーカスサマリを取得"""
    # 日付バリデーション
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    try:
        summary = calculate_daily_summary(date)
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サマリ計算エラー: {str(e)}")


@app.get("/api/trend", response_model=TrendResponse)
async def get_trend_data(
    from_date: str = Query(..., alias="from", description="開始日 (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="終了日 (YYYY-MM-DD)")
):
    """期間推移データを取得"""
    # 日付バリデーション
    if not validate_date_format(from_date):
        raise HTTPException(status_code=400, detail="開始日の形式が正しくありません (YYYY-MM-DD)")
    
    if not validate_date_format(to_date):
        raise HTTPException(status_code=400, detail="終了日の形式が正しくありません (YYYY-MM-DD)")
    
    try:
        # 日付範囲チェック
        date_list = get_date_range(from_date, to_date)
        if len(date_list) > 90:  # 最大90日間に制限
            raise HTTPException(status_code=400, detail="期間は90日以内で指定してください")
        
        trend_data = calculate_trend_data(from_date, to_date)
        return trend_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推移データ計算エラー: {str(e)}")


# === カテゴリエンドポイント ===

@app.get("/api/categories", response_model=List[CategoryModel])
async def get_categories():
    """全カテゴリを順序付きで取得"""
    try:
        db_categories = get_all_categories()
        
        # DBCategoryをCategoryModelに変換
        categories = []
        for db_cat in db_categories:
            categories.append(CategoryModel(
                code=db_cat.code,
                label=db_cat.label,
                weight=db_cat.weight,
                color=db_cat.color,
                order_index=db_cat.order_index
            ))
        
        return categories
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"カテゴリ取得エラー: {str(e)}")


# === AI提案エンドポイント ===

@app.get("/api/ai/suggestions/{date}", response_model=AIResponse)
async def get_ai_suggestions(date: str):
    """
    指定日の改善提案を取得
    LLM_API_KEY環境変数があればLLM利用、なければルールベース
    """
    # 日付バリデーション
    if not validate_date_format(date):
        raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
    
    try:
        suggestions = get_daily_suggestions(date)
        return suggestions
        
    except Exception as e:
        # 提案生成エラーでも200を返す（フォールバック付き）
        return AIResponse(
            suggestions=[f"提案生成エラー: {str(e)}"],
            summary="システムエラーにより提案を生成できませんでした。",
            is_ai_generated=False
        )


# === システム情報エンドポイント ===

@app.get("/api/stats")
async def get_system_stats():
    """システム統計情報を取得"""
    try:
        db_stats = get_database_stats()
        
        # 環境変数チェック
        has_llm_key = bool(os.getenv('LLM_API_KEY'))
        
        return {
            "database": db_stats,
            "environment": {
                "has_llm_api_key": has_llm_key,
                "current_date": get_today()
            },
            "api_version": "1.0.0"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計取得エラー: {str(e)}")


# === デバッグエンドポイント（開発用） ===

@app.get("/api/debug/reset")
async def debug_reset_database():
    """デバッグ用：データベースを完全リセット"""
    try:
        from .db import reset_database
        reset_database()
        
        return {
            "message": "データベースをリセットしました",
            "warning": "全データが削除されました"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リセットエラー: {str(e)}")


# === アプリケーション起動時処理 ===

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化処理"""
    print("=== Focus Ring API Server Started ===")
    
    # データベース初期化
    try:
        init_database()
        print("OK: Database initialized")
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
    
    # 環境変数チェック
    llm_key = os.getenv('LLM_API_KEY')
    if llm_key:
        print("OK: LLM API Key detected")
    else:
        print("INFO: LLM API Key not set (rule-based suggestions only)")
    
    print("OK: Focus Ring API Server ready")
    print("INFO: Access http://localhost:8000 in your browser")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    print("INFO: Focus Ring API Server stopped")


# === メイン実行（開発用） ===

if __name__ == "__main__":
    import uvicorn
    
    # 開発サーバー起動
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )