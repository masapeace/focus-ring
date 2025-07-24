/**
 * Focus Ring - JavaScriptフロントエンド
 * 1日行動×集中タイムトラッカーのクライアントサイド機能
 */

// === グローバル変数とアプリケーション状態 ===
let currentDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
let dayData = []; // 80ブロックのデータ
let categories = []; // カテゴリ一覧
let recentCategories = []; // 最近使用カテゴリ
let currentChart = null; // Chart.jsインスタンス
let currentSlotIndex = null; // 現在編集中のスロット

// DOM要素キャッシュ
const elements = {};

// === 初期化処理 ===
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🎯 Focus Ring 初期化開始');
    
    // DOM要素をキャッシュ
    cacheElements();
    
    // イベントリスナー設定
    setupEventListeners();
    
    // APIの初期化
    await initializeAPI();
    
    // カテゴリ一覧取得
    await loadCategories();
    
    // 今日のデータ読み込み
    await loadDayData(currentDate);
    
    console.log('✅ Focus Ring 初期化完了');
});

// === DOM要素キャッシュ ===
function cacheElements() {
    elements.currentDate = document.getElementById('current-date');
    elements.prevDay = document.getElementById('prev-day');
    elements.nextDay = document.getElementById('next-day');
    elements.todayBtn = document.getElementById('today-btn');
    elements.timeGrid = document.getElementById('time-grid');
    elements.filledCount = document.getElementById('filled-count');
    elements.categoryLegend = document.getElementById('category-legend');
    
    // サマリ要素
    elements.focusScore = document.getElementById('focus-score');
    elements.productiveHours = document.getElementById('productive-hours');
    elements.deepStreak = document.getElementById('deep-streak');
    elements.distractRatio = document.getElementById('distract-ratio');
    
    // チャート要素
    elements.activityChart = document.getElementById('activityChart');
    elements.chartDaily = document.getElementById('chart-daily');
    elements.chartWeekly = document.getElementById('chart-weekly');
    
    // 提案要素
    elements.suggestionSummary = document.getElementById('suggestion-summary');
    elements.suggestionsList = document.getElementById('suggestions-list');
    elements.refreshSuggestions = document.getElementById('refresh-suggestions');
    
    // モーダル要素
    elements.categoryModal = document.getElementById('category-modal');
    elements.detailModal = document.getElementById('detail-modal');
    elements.loading = document.getElementById('loading');
    elements.notification = document.getElementById('notification');
}

// === イベントリスナー設定 ===
function setupEventListeners() {
    // 日付ナビゲーション
    elements.prevDay.addEventListener('click', () => navigateDate(-1));
    elements.nextDay.addEventListener('click', () => navigateDate(1));
    elements.todayBtn.addEventListener('click', () => goToToday());
    
    // チャート切替
    elements.chartDaily.addEventListener('click', () => switchChart('daily'));
    elements.chartWeekly.addEventListener('click', () => switchChart('weekly'));
    
    // 提案更新
    elements.refreshSuggestions.addEventListener('click', () => loadSuggestions());
    
    // モーダル関連
    setupModalListeners();
    
    // キーボードショートカット
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// === API通信ラッパー ===
class FocusRingAPI {
    static async request(url, options = {}) {
        try {
            showLoading(true);
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showNotification(error.message, 'error');
            throw error;
        } finally {
            showLoading(false);
        }
    }
    
    static async init() {
        return this.request('/api/init', { method: 'POST' });
    }
    
    static async getDayData(date) {
        return this.request(`/api/day/${date}`);
    }
    
    static async updateBlock(blockData) {
        return this.request('/api/block', {
            method: 'POST',
            body: JSON.stringify(blockData)
        });
    }
    
    static async getDailySummary(date) {
        return this.request(`/api/summary/${date}`);
    }
    
    static async getTrendData(fromDate, toDate) {
        return this.request(`/api/trend?from=${fromDate}&to=${toDate}`);
    }
    
    static async getCategories() {
        return this.request('/api/categories');
    }
    
    static async getSuggestions(date) {
        return this.request(`/api/ai/suggestions/${date}`);
    }
}

// === API初期化 ===
async function initializeAPI() {
    try {
        await FocusRingAPI.init();
        showNotification('データベース初期化完了', 'success');
    } catch (error) {
        console.warn('API初期化エラー:', error);
    }
}

// === カテゴリ読み込み ===
async function loadCategories() {
    try {
        categories = await FocusRingAPI.getCategories();
        console.log(`📂 ${categories.length} カテゴリ読み込み完了`);
        
        // カテゴリ凡例を更新
        updateCategoryLegend();
        
        // 最近使用カテゴリを初期化（ローカルストレージから）
        loadRecentCategories();
        
    } catch (error) {
        console.error('カテゴリ読み込みエラー:', error);
    }
}

// === 日次データ読み込み ===
async function loadDayData(date) {
    try {
        dayData = await FocusRingAPI.getDayData(date);
        console.log(`📅 ${date} のデータ読み込み完了`);
        
        // UI更新
        updateDateDisplay(date);
        updateTimeGrid();
        updateFilledCount();
        await updateDailySummary();
        await loadSuggestions();
        
    } catch (error) {
        console.error('日次データ読み込みエラー:', error);
    }
}

// === タイムグリッド生成 ===
function updateTimeGrid() {
    elements.timeGrid.innerHTML = '';
    
    for (let i = 0; i < 80; i++) {
        const cell = createTimeCell(i);
        elements.timeGrid.appendChild(cell);
    }
}

function createTimeCell(slotIndex) {
    const block = dayData[slotIndex];
    const cell = document.createElement('div');
    cell.className = 'time-cell';
    cell.dataset.slotIndex = slotIndex;
    
    // 時刻表示
    const timeLabel = document.createElement('div');
    timeLabel.className = 'time-label';
    timeLabel.textContent = block.start_time;
    cell.appendChild(timeLabel);
    
    // カテゴリに応じたスタイル適用
    if (block.category) {
        const category = categories.find(c => c.code === block.category);
        if (category) {
            cell.classList.add('filled', category.color);
            cell.title = `${block.start_time} - ${category.label}`;
            
            // 集中度インジケーター
            if (block.focus) {
                const focusIndicator = document.createElement('div');
                focusIndicator.className = 'focus-indicator';
                focusIndicator.style.background = getFocusColor(block.focus);
                focusIndicator.title = `集中度: ${block.focus}/5`;
                cell.appendChild(focusIndicator);
            }
        }
    } else {
        cell.title = `${block.start_time} - 未入力`;
    }
    
    // クリックイベント
    cell.addEventListener('click', () => openCategoryModal(slotIndex));
    cell.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        openDetailModal(slotIndex);
    });
    
    return cell;
}

// === 日付ナビゲーション ===
function navigateDate(days) {
    const date = new Date(currentDate);
    date.setDate(date.getDate() + days);
    const newDate = date.toISOString().split('T')[0];
    
    currentDate = newDate;
    loadDayData(currentDate);
}

function goToToday() {
    const today = new Date().toISOString().split('T')[0];
    if (currentDate !== today) {
        currentDate = today;
        loadDayData(currentDate);
    }
}

function updateDateDisplay(date) {
    elements.currentDate.textContent = date;
    
    // 今日かどうかで今日ボタンの表示を制御
    const today = new Date().toISOString().split('T')[0];
    elements.todayBtn.style.display = (date === today) ? 'none' : 'inline-block';
}

// === カテゴリ選択モーダル ===
function openCategoryModal(slotIndex) {
    currentSlotIndex = slotIndex;
    const block = dayData[slotIndex];
    
    // モーダルタイトル更新
    document.getElementById('modal-time').textContent = block.start_time;
    
    // カテゴリボタン生成
    updateCategoryButtons();
    
    // モーダル表示
    elements.categoryModal.classList.add('active');
}

function updateCategoryButtons() {
    // 最近使用カテゴリ
    const recentContainer = document.getElementById('recent-categories');
    recentContainer.innerHTML = '';
    
    recentCategories.slice(0, 5).forEach(categoryCode => {
        const category = categories.find(c => c.code === categoryCode);
        if (category) {
            const button = createCategoryButton(category);
            recentContainer.appendChild(button);
        }
    });
    
    // 全カテゴリ
    const allContainer = document.getElementById('all-categories');
    allContainer.innerHTML = '';
    
    categories.forEach(category => {
        const button = createCategoryButton(category);
        allContainer.appendChild(button);
    });
}

function createCategoryButton(category) {
    const button = document.createElement('button');
    button.className = `category-btn ${category.color}`;
    button.textContent = category.label;
    button.title = `重み: ${category.weight}`;
    
    button.addEventListener('click', () => {
        selectCategory(category.code);
    });
    
    return button;
}

async function selectCategory(categoryCode) {
    try {
        await updateBlock(currentSlotIndex, { category: categoryCode });
        
        // 最近使用カテゴリを更新
        updateRecentCategories(categoryCode);
        
        // モーダルを閉じる
        closeCategoryModal();
        
        showNotification('カテゴリを更新しました', 'success');
        
    } catch (error) {
        console.error('カテゴリ選択エラー:', error);
    }
}

function closeCategoryModal() {
    elements.categoryModal.classList.remove('active');
    currentSlotIndex = null;
}

// === 詳細編集モーダル ===
function openDetailModal(slotIndex) {
    currentSlotIndex = slotIndex;
    const block = dayData[slotIndex];
    
    // モーダルタイトル更新
    document.getElementById('detail-time').textContent = block.start_time;
    
    // フォーム初期化
    populateDetailForm(block);
    
    // モーダル表示
    elements.detailModal.classList.add('active');
}

function populateDetailForm(block) {
    // カテゴリセレクト
    const categorySelect = document.getElementById('detail-category');
    categorySelect.innerHTML = '<option value="">未選択</option>';
    
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category.code;
        option.textContent = category.label;
        if (block.category === category.code) {
            option.selected = true;
        }
        categorySelect.appendChild(option);
    });
    
    // 集中度ボタン
    updateFocusButtons(block.focus);
    
    // メモ
    const memoTextarea = document.getElementById('detail-memo');
    memoTextarea.value = block.memo || '';
    updateMemoCount();
}

function updateFocusButtons(focusLevel) {
    const buttons = document.querySelectorAll('.focus-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        const focus = parseInt(btn.dataset.focus);
        if (focus === focusLevel) {
            btn.classList.add('active');
        }
    });
    
    const display = document.getElementById('detail-focus-display');
    display.textContent = focusLevel ? `${focusLevel}/5` : '未設定';
}

function updateMemoCount() {
    const memo = document.getElementById('detail-memo').value;
    document.getElementById('memo-count').textContent = memo.length;
}

async function saveDetailForm() {
    try {
        const categorySelect = document.getElementById('detail-category');
        const focusBtn = document.querySelector('.focus-btn.active');
        const memo = document.getElementById('detail-memo').value;
        
        const data = {
            category: categorySelect.value || null,
            focus: focusBtn ? parseInt(focusBtn.dataset.focus) || null : null,
            memo: memo.trim() || null
        };
        
        await updateBlock(currentSlotIndex, data);
        
        closeDetailModal();
        showNotification('詳細を更新しました', 'success');
        
    } catch (error) {
        console.error('詳細保存エラー:', error);
    }
}

function clearDetailForm() {
    if (confirm('このブロックをクリアしますか？')) {
        updateBlock(currentSlotIndex, { category: null, focus: null, memo: null });
        closeDetailModal();
    }
}

function closeDetailModal() {
    elements.detailModal.classList.remove('active');
    currentSlotIndex = null;
}

// === ブロック更新 ===
async function updateBlock(slotIndex, data) {
    const blockData = {
        date: currentDate,
        slot_index: slotIndex,
        ...data
    };
    
    await FocusRingAPI.updateBlock(blockData);
    
    // ローカルデータ更新
    Object.assign(dayData[slotIndex], data);
    
    // UI更新
    updateTimeGrid();
    updateFilledCount();
    await updateDailySummary();
    
    // 提案も更新
    setTimeout(() => loadSuggestions(), 500);
}

// === サマリ更新 ===
async function updateDailySummary() {
    try {
        const summary = await FocusRingAPI.getDailySummary(currentDate);
        
        // メトリクス表示更新
        elements.focusScore.textContent = summary.focus_score.toFixed(1);
        elements.productiveHours.textContent = `${summary.productive_hours}h`;
        elements.deepStreak.textContent = `${summary.deep_streak_max * 15}分`;
        elements.distractRatio.textContent = `${(summary.distract_ratio * 100).toFixed(1)}%`;
        
        // チャート更新
        updateChart(summary);
        
    } catch (error) {
        console.error('サマリ更新エラー:', error);
    }
}

// === Chart.js連携 ===
function updateChart(summary) {
    const ctx = elements.activityChart.getContext('2d');
    
    if (currentChart) {
        currentChart.destroy();
    }
    
    if (elements.chartDaily.classList.contains('active')) {
        createDailyChart(ctx, summary);
    } else {
        createWeeklyChart(ctx);
    }
}

function createDailyChart(ctx, summary) {
    currentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['生産的', '妨害的', '中性', '未入力'],
            datasets: [{
                data: [
                    summary.productive_blocks,
                    summary.distract_blocks,
                    summary.neutral_blocks,
                    80 - summary.total_filled
                ],
                backgroundColor: [
                    '#28a745',  // 緑：生産的
                    '#dc3545',  // 赤：妨害的
                    '#6c757d',  // グレー：中性
                    '#e9ecef'   // 薄グレー：未入力
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                }
            }
        }
    });
}

async function createWeeklyChart(ctx) {
    try {
        // 過去7日間の推移データを取得
        const endDate = currentDate;
        const startDate = new Date(currentDate);
        startDate.setDate(startDate.getDate() - 6);
        const startDateStr = startDate.toISOString().split('T')[0];
        
        const trendData = await FocusRingAPI.getTrendData(startDateStr, endDate);
        
        currentChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.trend_data.map(d => {
                    const date = new Date(d.date);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                }),
                datasets: [
                    {
                        label: 'フォーカススコア',
                        data: trendData.trend_data.map(d => d.focus_score),
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: '生産的時間',
                        data: trendData.trend_data.map(d => d.productive_hours),
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'スコア'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '時間'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('週間チャート作成エラー:', error);
    }
}

function switchChart(type) {
    // ボタンの状態更新
    elements.chartDaily.classList.toggle('active', type === 'daily');
    elements.chartWeekly.classList.toggle('active', type === 'weekly');
    
    // チャート更新は次回のサマリ更新で行われる
    updateDailySummary();
}

// === 改善提案 ===
async function loadSuggestions() {
    try {
        const response = await FocusRingAPI.getSuggestions(currentDate);
        
        // 総括表示
        elements.suggestionSummary.textContent = response.summary;
        
        // 提案リスト表示
        elements.suggestionsList.innerHTML = '';
        response.suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.textContent = suggestion;
            elements.suggestionsList.appendChild(li);
        });
        
        // AI生成かどうかの表示
        const aiIndicator = response.is_ai_generated ? '🤖 AI' : '📋 ルール';
        console.log(`💡 改善提案更新完了 (${aiIndicator})`);
        
    } catch (error) {
        console.error('改善提案読み込みエラー:', error);
    }
}

// === ユーティリティ関数 ===
function updateFilledCount() {
    const filledCount = dayData.filter(block => block.category).length;
    elements.filledCount.textContent = filledCount;
}

function updateCategoryLegend() {
    elements.categoryLegend.innerHTML = '';
    
    categories.forEach(category => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        
        const color = document.createElement('div');
        color.className = `legend-color ${category.color}`;
        
        const label = document.createElement('span');
        label.textContent = category.label;
        
        const weight = document.createElement('span');
        weight.className = 'legend-weight';
        weight.textContent = category.weight > 0 ? `+${category.weight}` : category.weight;
        
        item.appendChild(color);
        item.appendChild(label);
        item.appendChild(weight);
        
        elements.categoryLegend.appendChild(item);
    });
}

function getFocusColor(focus) {
    const colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#007bff'];
    return colors[focus - 1] || '#6c757d';
}

function loadRecentCategories() {
    const stored = localStorage.getItem('focusring_recent_categories');
    recentCategories = stored ? JSON.parse(stored) : [];
}

function updateRecentCategories(categoryCode) {
    // 既存項目を削除
    recentCategories = recentCategories.filter(code => code !== categoryCode);
    
    // 先頭に追加
    recentCategories.unshift(categoryCode);
    
    // 最大10件まで
    recentCategories = recentCategories.slice(0, 10);
    
    // ローカルストレージに保存
    localStorage.setItem('focusring_recent_categories', JSON.stringify(recentCategories));
}

function showLoading(show) {
    elements.loading.classList.toggle('active', show);
}

function showNotification(message, type = 'success') {
    const notification = elements.notification;
    notification.className = `notification ${type} active`;
    notification.querySelector('.notification-text').textContent = message;
    
    // 3秒後に自動で閉じる
    setTimeout(() => {
        notification.classList.remove('active');
    }, 3000);
}

function handleKeyboardShortcuts(e) {
    // ESC: モーダルを閉じる
    if (e.key === 'Escape') {
        closeCategoryModal();
        closeDetailModal();
    }
    
    // Ctrl+左矢印: 前日
    if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateDate(-1);
    }
    
    // Ctrl+右矢印: 翌日
    if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        navigateDate(1);
    }
    
    // Ctrl+T: 今日へ
    if (e.ctrlKey && e.key === 't') {
        e.preventDefault();
        goToToday();
    }
}

// === モーダルイベントリスナー ===
function setupModalListeners() {
    // カテゴリモーダル
    document.getElementById('modal-close').addEventListener('click', closeCategoryModal);
    elements.categoryModal.addEventListener('click', (e) => {
        if (e.target === elements.categoryModal) {
            closeCategoryModal();
        }
    });
    
    // 詳細モーダル
    document.getElementById('detail-close').addEventListener('click', closeDetailModal);
    document.getElementById('detail-save').addEventListener('click', saveDetailForm);
    document.getElementById('detail-clear').addEventListener('click', clearDetailForm);
    document.getElementById('detail-cancel').addEventListener('click', closeDetailModal);
    
    elements.detailModal.addEventListener('click', (e) => {
        if (e.target === elements.detailModal) {
            closeDetailModal();
        }
    });
    
    // 集中度ボタン
    document.querySelectorAll('.focus-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            updateFocusButtons(parseInt(btn.dataset.focus) || null);
        });
    });
    
    // メモ文字数カウント
    document.getElementById('detail-memo').addEventListener('input', updateMemoCount);
    
    // 通知クローズ
    document.querySelector('.notification-close').addEventListener('click', () => {
        elements.notification.classList.remove('active');
    });
}

// === エクスポート（開発用） ===
window.FocusRing = {
    currentDate,
    dayData,
    categories,
    loadDayData,
    updateBlock,
    API: FocusRingAPI
};

console.log('🎯 Focus Ring JavaScript 読み込み完了');