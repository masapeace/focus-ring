# 🎯 Focus Ring - 1日行動×集中タイムトラッカー

## 📖 概要

**Focus Ring** は、休日や休暇日の行動を15分単位で追跡し、自動的にフォーカススコアを計算して生産性向上をサポートするWebアプリケーションです。

### 🎯 目的
- 勉強時間と集中度の改善
- YouTubeやSNSに流される時間の削減
- 「今日も入力できた」という成功体験の積み重ね
- 操作回数を最小にした簡単入力システム

### ⏰ 対象時間
- **1日の範囲**: 04:00 〜 23:45（起床〜就寝）
- **時間刻み**: 15分単位（全80ブロック）
- **想定ユーザー**: 04:00頃起床、22:00就寝の生活リズム

## 🛠️ 技術スタック

### バックエンド
- **Python 3.11**
- **FastAPI** - REST API サーバー
- **SQLite** - データベース（ローカル）
- **Pydantic** - データバリデーション

### フロントエンド
- **HTML5 + CSS3 + JavaScript (ES6+)**
- **Chart.js** - データ可視化
- **レスポンシブデザイン**

### 特徴
- 🔒 **認証不要** - ローカル環境で即座に利用開始
- 📱 **レスポンシブ対応** - PC・タブレット・スマートフォン
- 🤖 **LLM連携オプション** - OpenAI APIによる高度な改善提案

## 📦 セットアップ

### 1. 前提条件
- Python 3.11 以上
- pip (Pythonパッケージマネージャー)

### 2. プロジェクトのクローンと移動
```bash
git clone <repository-url>
cd focus_ring
```

### 3. 仮想環境の作成と有効化
```bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 4. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 5. アプリケーションの起動
```bash
# メインディレクトリで実行
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 初期化とアクセス
1. ブラウザで `http://localhost:8000` にアクセス
2. 初回アクセス時に自動的にデータベースが初期化されます
3. または手動で `POST http://localhost:8000/api/init` を実行

## 🎮 使い方

### 基本操作
1. **日付ナビゲーション**: ← → ボタンで日付を移動、「今日」ボタンで今日に戻る
2. **ブロック入力**: タイムグリッドのセルをクリックしてカテゴリを選択
3. **詳細編集**: セルを右クリックして集中度・メモを入力
4. **リアルタイム更新**: 入力と同時にフォーカススコアと改善提案が更新

### カテゴリ一覧（16種類）

| カテゴリ | 重み | 説明 |
|----------|------|------|
| 📚 勉強 | +3 | 学習・研究活動 |
| 🌍 英語 | +4 | 英語学習 |
| 🤖 AI学習 | +4 | AI・機械学習関連 |
| 💼 作業ログ | +4 | 仕事・プロジェクト |
| ✍️ ブログ | +3 | 執筆・アウトプット |
| 🐕 散歩 | +2 | ペットとの散歩 |
| 🌱 農作業 | +2 | 農業・園芸 |
| 🏠 家事 | +1 | 掃除・整理整頓 |
| 📋 管理 | +1 | 事務・管理作業 |
| 💪 健康 | +2 | 運動・健康管理 |
| 🍽️ 食事 | 0 | 食事時間 |
| 😴 休憩 | 0 | 短時間の休憩 |
| 🛏️ 睡眠 | 0 | 睡眠・仮眠 |
| 📺 動画 | -2 | YouTube・動画視聴 |
| 📱 SNS | -3 | SNS・ソーシャルメディア |
| ❓ 無駄時間 | -4 | 特に目的のない時間 |

## 📊 フォーカススコア計算式

Focus Ring の中核となるスコア計算ロジック：

### 基本計算式
```
focus_score = raw_score + deep_streak_max - penalty
```

### 詳細計算
1. **生スコア (raw_score)**
   ```
   raw_score = Σ weight(category)
   ```
   - 各ブロックのカテゴリ重みの合計

2. **深い集中ストリーク (deep_streak_max)**
   ```
   deep_streak_max = 連続する生産的ブロック（weight > 0）の最大数
   ```
   - 連続して集中した時間を評価
   - 15分 × ストリーク数 = 連続集中時間

3. **コンテキストスイッチペナルティ (penalty)**
   ```
   context_switch = カテゴリ切替回数
   penalty = max(0, context_switch - total_filled/8) * 0.5
   ```
   - 過度なタスク切替にペナルティ
   - 8ブロック（2時間）に1回の切替は許容

### 追加指標
- **productive_blocks**: 生産的ブロック数（重み > 0）
- **distract_blocks**: 妨害ブロック数（重み < 0）
- **productive_hours**: 生産的時間 = productive_blocks × 0.25
- **distract_ratio**: 妨害時間割合 = distract_blocks / (productive + distract)
- **avg_focus_productive**: 生産的ブロックの平均集中度

## 💡 改善提案ロジック

### ルールベース提案（基本）
1. **妨害時間チェック**
   - `distract_ratio > 0.2` → 動画・SNS時間の削減を提案

2. **最低生産時間チェック**
   - `productive_blocks < 12` → 最低3時間の生産的活動を推奨

3. **集中連続性チェック**
   - `deep_streak_max < 4` → 朝の2時間ブロック化を提案

4. **タスク切替チェック**
   - 過度なカテゴリ切替 → 同種作業のまとめを提案

5. **入力継続チェック**
   - `total_filled < 40` → 記録習慣化を推奨

### LLM連携提案（オプション）
環境変数 `LLM_API_KEY` を設定することで、OpenAI GPT を使用した詳細な改善提案が利用可能：

```bash
export LLM_API_KEY="your-openai-api-key"
```

**LLM提案の特徴**:
- 個人の行動パターンを深く分析
- より具体的で実行可能な改善案
- 時間帯別生産性の考慮
- パーソナライズされたアドバイス

## 🔌 API 仕様

### エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|----------|---------------|------|
| POST | `/api/init` | データベース初期化 |
| GET | `/api/day/{date}` | 指定日の80ブロックデータ取得 |
| POST | `/api/block` | 単一ブロック更新 |
| POST | `/api/bulk` | 複数ブロック一括更新 |
| GET | `/api/summary/{date}` | 日次サマリ取得 |
| GET | `/api/trend?from={date}&to={date}` | 期間推移データ取得 |
| GET | `/api/categories` | カテゴリ一覧取得 |
| GET | `/api/ai/suggestions/{date}` | 改善提案取得 |

### リクエスト例

#### ブロック更新
```json
POST /api/block
{
  "date": "2024-01-15",
  "slot_index": 12,
  "category": "STUDY",
  "focus": 4,
  "memo": "数学の勉強"
}
```

#### 日次サマリレスポンス
```json
{
  "date": "2024-01-15",
  "focus_score": 12.5,
  "productive_blocks": 18,
  "distract_blocks": 3,
  "productive_hours": 4.5,
  "distract_ratio": 0.143,
  "deep_streak_max": 6
}
```

## 📁 プロジェクト構造

```
focus_ring/
├── app/
│   ├── __init__.py          # パッケージ初期化
│   ├── main.py              # FastAPI メインアプリケーション
│   ├── models.py            # Pydantic データモデル
│   ├── db.py                # SQLite データベース操作
│   ├── utils.py             # ユーティリティ関数
│   ├── summarizer.py        # フォーカススコア計算
│   ├── suggestions.py       # 改善提案エンジン
│   └── static/
│       ├── index.html       # メインページ
│       ├── style.css        # スタイルシート
│       └── app.js           # フロントエンド JavaScript
├── requirements.txt         # Python依存関係
├── README.md               # このファイル
└── focus_ring.db           # SQLiteデータベース（自動生成）
```

## 🎨 画面構成

### メイン画面
- **左側**: 80マスタイムグリッド + カテゴリ凡例
- **右側**: 今日のサマリ + チャート + 改善提案

### モーダル
- **カテゴリ選択**: 最近使用5つ + 全カテゴリ
- **詳細編集**: カテゴリ・集中度・メモの詳細設定

### キーボードショートカット
- `Ctrl + ←/→`: 前日/翌日移動
- `Ctrl + T`: 今日に移動
- `ESC`: モーダルを閉じる

## 🚀 将来の拡張案

### 1. 🖱️ ドラッグ塗り機能
複数ブロックを一度に同じカテゴリで塗りつぶし可能にする

### 2. 📅 週次目標設定
週単位での生産時間目標設定と達成率追跡

### 3. 📱 PWA化
オフライン対応とスマートフォンアプリライクな操作性

### 4. 📄 CSVエクスポート
データをCSV形式でエクスポートして外部分析を可能にする

### 5. ⚙️ カテゴリCRUD
ユーザーが独自にカテゴリを追加・編集・削除できる機能

### 6. 🌊 フロー状態検出
集中度と時間から「フロー状態」を自動検出・分析

### 7. 📝 LLM 3行レビュー
AIによる1日の行動パターンの3行要約とコーチング

### 8. 📋 計画 vs 実績比較
事前に立てた計画と実際の行動を比較分析

### 9. ☁️ Supabase同期
クラウドデータベースとの同期でマルチデバイス対応

### 10. ⏰ 未入力リマインド
Webプッシュ通知による入力忘れ防止機能

## 🐛 トラブルシューティング

### ポートが使用中の場合
```bash
# 別のポートで起動
uvicorn app.main:app --port 8001
```

### データベースリセット
```bash
# 開発用エンドポイント
curl -X GET http://localhost:8000/api/debug/reset
```

### Python環境の確認
```bash
python --version  # 3.11以上であることを確認
pip list          # インストール済みパッケージ確認
```

## 📞 サポート

### API ドキュメント
起動後に以下にアクセス：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### システム統計
- `http://localhost:8000/api/stats` でシステム情報確認

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

---

**Happy Focus! 🎯**

今日も集中して、より良い明日を作りましょう。