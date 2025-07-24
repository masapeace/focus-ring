/**
 * Focus Ring - Static Version with LocalStorage
 * 静的HTML版：サーバーなしでローカルストレージを使用
 */

// ===== 定数定義 =====

const CATEGORIES = [
    { code: "STUDY", label: "📚 勉強", weight: 3, color: "#4CAF50", order_index: 0 },
    { code: "ENGLISH", label: "🌍 英語", weight: 4, color: "#2196F3", order_index: 1 },
    { code: "AI_LEARNING", label: "🤖 AI学習", weight: 4, color: "#9C27B0", order_index: 2 },
    { code: "WORK_LOG", label: "💼 作業ログ", weight: 4, color: "#FF9800", order_index: 3 },
    { code: "BLOG", label: "✍️ ブログ", weight: 3, color: "#795548", order_index: 4 },
    { code: "WALK", label: "🐕 散歩", weight: 2, color: "#8BC34A", order_index: 5 },
    { code: "FARMING", label: "🌱 農作業", weight: 2, color: "#4CAF50", order_index: 6 },
    { code: "HOUSEWORK", label: "🏠 家事", weight: 1, color: "#607D8B", order_index: 7 },
    { code: "MANAGEMENT", label: "📋 管理", weight: 1, color: "#9E9E9E", order_index: 8 },
    { code: "HEALTH", label: "💪 健康", weight: 2, color: "#F44336", order_index: 9 },
    { code: "MEAL", label: "🍽️ 食事", weight: 0, color: "#FFC107", order_index: 10 },
    { code: "REST", label: "😴 休憩", weight: 0, color: "#CDDC39", order_index: 11 },
    { code: "SLEEP", label: "🛏️ 睡眠", weight: 0, color: "#3F51B5", order_index: 12 },
    { code: "VIDEO", label: "📺 動画", weight: -2, color: "#E91E63", order_index: 13 },
    { code: "SNS", label: "📱 SNS", weight: -3, color: "#FF5722", order_index: 14 },
    { code: "WASTE", label: "❓ 無駄時間", weight: -4, color: "#424242", order_index: 15 }
];

// ===== グローバル変数 =====

let currentDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
let selectedSlot = null;
let activityChart = null;

// ===== ユーティリティ関数 =====

function getStorageKey(date, slotIndex) {
    return `focus_ring_${date}_${slotIndex}`;
}

function getBlockData(date, slotIndex) {
    const key = getStorageKey(date, slotIndex);
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : { category: null, focus: null, memo: null };
}

function saveBlockData(date, slotIndex, data) {
    const key = getStorageKey(date, slotIndex);
    localStorage.setItem(key, JSON.stringify({
        ...data,
        updated_at: new Date().toISOString()
    }));
}

function getCategoryByCode(code) {
    return CATEGORIES.find(cat => cat.code === code);
}

function formatTime(slotIndex) {
    const startHour = 4;
    const totalMinutes = startHour * 60 + slotIndex * 15;
    const hours = Math.floor(totalMinutes / 60) % 24;
    const minutes = totalMinutes % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

function calculateDailySummary(date) {
    let productiveBlocks = 0;
    let distractBlocks = 0;
    let totalFilled = 0;
    let focusScore = 0;

    for (let i = 0; i < 80; i++) {
        const blockData = getBlockData(date, i);
        if (blockData.category) {
            totalFilled++;
            const category = getCategoryByCode(blockData.category);
            if (category) {
                if (category.weight > 0) productiveBlocks++;
                if (category.weight < 0) distractBlocks++;
                focusScore += category.weight;
            }
        }
    }

    return {
        focus_score: focusScore,
        productive_blocks: productiveBlocks,
        distract_blocks: distractBlocks,
        productive_hours: (productiveBlocks * 0.25),
        distract_ratio: totalFilled > 0 ? (distractBlocks / totalFilled) : 0,
        deep_streak_max: Math.max(4, Math.floor(productiveBlocks / 4)) // 簡易計算
    };
}

// ===== UI生成関数 =====

function generateTimeGrid() {
    const gridContainer = document.getElementById('time-grid');
    if (!gridContainer) return;

    gridContainer.innerHTML = '';

    for (let i = 0; i < 80; i++) {
        const timeSlot = document.createElement('div');
        timeSlot.className = 'time-slot';
        timeSlot.dataset.slotIndex = i;
        
        const timeLabel = document.createElement('div');
        timeLabel.className = 'time-label';
        timeLabel.textContent = formatTime(i);
        
        const blockContent = document.createElement('div');
        blockContent.className = 'block-content';
        
        timeSlot.appendChild(timeLabel);
        timeSlot.appendChild(blockContent);
        
        // クリックイベント
        timeSlot.addEventListener('click', () => openCategoryModal(i));
        timeSlot.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            openDetailModal(i);
        });
        
        gridContainer.appendChild(timeSlot);
    }
}

function generateCategoryLegend() {
    const legendContainer = document.getElementById('category-legend');
    if (!legendContainer) return;

    legendContainer.innerHTML = '';

    CATEGORIES.forEach(category => {
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        legendItem.innerHTML = `
            <div class="legend-color" style="background-color: ${category.color}"></div>
            <span class="legend-label">${category.label}</span>
            <span class="legend-weight">(${category.weight > 0 ? '+' : ''}${category.weight})</span>
        `;
        legendContainer.appendChild(legendItem);
    });
}

function updateTimeGrid() {
    const timeSlots = document.querySelectorAll('.time-slot');
    let filledCount = 0;

    timeSlots.forEach((slot, index) => {
        const blockData = getBlockData(currentDate, index);
        const blockContent = slot.querySelector('.block-content');
        
        if (blockData.category) {
            filledCount++;
            const category = getCategoryByCode(blockData.category);
            if (category) {
                blockContent.style.backgroundColor = category.color;
                blockContent.textContent = category.label;
                slot.classList.add('filled');
            }
        } else {
            blockContent.style.backgroundColor = '';
            blockContent.textContent = '';
            slot.classList.remove('filled');
        }
    });

    // 統計更新
    const filledCountElement = document.getElementById('filled-count');
    if (filledCountElement) {
        filledCountElement.textContent = filledCount;
    }
}

function updateSummary() {
    const summary = calculateDailySummary(currentDate);
    
    const focusScoreEl = document.getElementById('focus-score');
    const productiveHoursEl = document.getElementById('productive-hours');
    const deepStreakEl = document.getElementById('deep-streak');
    const distractRatioEl = document.getElementById('distract-ratio');
    
    if (focusScoreEl) focusScoreEl.textContent = summary.focus_score.toFixed(1);
    if (productiveHoursEl) productiveHoursEl.textContent = summary.productive_hours.toFixed(1) + 'h';
    if (deepStreakEl) deepStreakEl.textContent = (summary.deep_streak_max * 15) + '分';
    if (distractRatioEl) distractRatioEl.textContent = (summary.distract_ratio * 100).toFixed(0) + '%';
}

// ===== モーダル機能 =====

function openCategoryModal(slotIndex) {
    selectedSlot = slotIndex;
    const modal = document.getElementById('category-modal');
    const timeLabel = document.getElementById('modal-time');
    
    if (timeLabel) timeLabel.textContent = formatTime(slotIndex);
    
    // カテゴリボタン生成
    const allCategoriesContainer = document.getElementById('all-categories');
    if (allCategoriesContainer) {
        allCategoriesContainer.innerHTML = '';
        
        CATEGORIES.forEach(category => {
            const button = document.createElement('button');
            button.className = 'category-btn';
            button.style.backgroundColor = category.color;
            button.textContent = category.label;
            button.addEventListener('click', () => selectCategory(category.code));
            allCategoriesContainer.appendChild(button);
        });
    }
    
    if (modal) modal.classList.add('active');
}

function selectCategory(categoryCode) {
    if (selectedSlot !== null) {
        saveBlockData(currentDate, selectedSlot, { category: categoryCode });
        updateTimeGrid();
        updateSummary();
        closeCategoryModal();
    }
}

function closeCategoryModal() {
    const modal = document.getElementById('category-modal');
    if (modal) modal.classList.remove('active');
    selectedSlot = null;
}

function openDetailModal(slotIndex) {
    selectedSlot = slotIndex;
    const modal = document.getElementById('detail-modal');
    const timeLabel = document.getElementById('detail-time');
    
    if (timeLabel) timeLabel.textContent = formatTime(slotIndex);
    
    // 既存データを読み込み
    const blockData = getBlockData(currentDate, slotIndex);
    const categorySelect = document.getElementById('detail-category');
    const memoTextarea = document.getElementById('detail-memo');
    
    if (categorySelect) categorySelect.value = blockData.category || '';
    if (memoTextarea) memoTextarea.value = blockData.memo || '';
    
    if (modal) modal.classList.add('active');
}

function closeDetailModal() {
    const modal = document.getElementById('detail-modal');
    if (modal) modal.classList.remove('active');
    selectedSlot = null;
}

// ===== イベントハンドラー =====

function initializeEventHandlers() {
    // 日付ナビゲーション
    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');
    const todayBtn = document.getElementById('today-btn');
    
    if (prevDayBtn) {
        prevDayBtn.addEventListener('click', () => {
            const date = new Date(currentDate);
            date.setDate(date.getDate() - 1);
            currentDate = date.toISOString().split('T')[0];
            updateCurrentDate();
            updateTimeGrid();
            updateSummary();
        });
    }
    
    if (nextDayBtn) {
        nextDayBtn.addEventListener('click', () => {
            const date = new Date(currentDate);
            date.setDate(date.getDate() + 1);
            currentDate = date.toISOString().split('T')[0];
            updateCurrentDate();
            updateTimeGrid();
            updateSummary();
        });
    }
    
    if (todayBtn) {
        todayBtn.addEventListener('click', () => {
            currentDate = new Date().toISOString().split('T')[0];
            updateCurrentDate();
            updateTimeGrid();
            updateSummary();
        });
    }
    
    // モーダル閉じる
    const modalClose = document.getElementById('modal-close');
    const detailClose = document.getElementById('detail-close');
    
    if (modalClose) modalClose.addEventListener('click', closeCategoryModal);
    if (detailClose) detailClose.addEventListener('click', closeDetailModal);
    
    // モーダル外クリックで閉じる
    const categoryModal = document.getElementById('category-modal');
    const detailModal = document.getElementById('detail-modal');
    
    if (categoryModal) {
        categoryModal.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                closeCategoryModal();
            }
        });
    }
    
    if (detailModal) {
        detailModal.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                closeDetailModal();
            }
        });
    }
    
    // 詳細モーダルの保存
    const detailSaveBtn = document.getElementById('detail-save');
    if (detailSaveBtn) {
        detailSaveBtn.addEventListener('click', () => {
            if (selectedSlot !== null) {
                const categorySelect = document.getElementById('detail-category');
                const memoTextarea = document.getElementById('detail-memo');
                
                const category = categorySelect ? categorySelect.value || null : null;
                const memo = memoTextarea ? memoTextarea.value || null : null;
                
                saveBlockData(currentDate, selectedSlot, { category, memo });
                updateTimeGrid();
                updateSummary();
                closeDetailModal();
            }
        });
    }
    
    // ESCキーでモーダルを閉じる
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeCategoryModal();
            closeDetailModal();
        }
    });
}

function updateCurrentDate() {
    const currentDateEl = document.getElementById('current-date');
    if (currentDateEl) {
        currentDateEl.textContent = currentDate;
    }
}

// ===== 初期化 =====

function initializeApp() {
    console.log('🎯 Focus Ring - Static Version Initializing...');
    
    // UI生成
    generateTimeGrid();
    generateCategoryLegend();
    
    // イベントハンドラー設定
    initializeEventHandlers();
    
    // 初期データ表示
    updateCurrentDate();
    updateTimeGrid();
    updateSummary();
    
    // 詳細モーダルのカテゴリ選択肢を生成
    const detailCategorySelect = document.getElementById('detail-category');
    if (detailCategorySelect) {
        detailCategorySelect.innerHTML = '<option value="">未選択</option>';
        CATEGORIES.forEach(category => {
            const option = document.createElement('option');
            option.value = category.code;
            option.textContent = category.label;
            detailCategorySelect.appendChild(option);
        });
    }
    
    console.log('✅ Focus Ring - Static Version Ready!');
}

// ===== アプリケーション起動 =====

document.addEventListener('DOMContentLoaded', initializeApp);