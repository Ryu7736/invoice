const InputImageElement = document.querySelector("#InputImage");
const ocrElement = document.querySelector("#ocr");
const resultElement = document.querySelector("#result");
const clickedElement = document.querySelector("#clicked")

ocrElement.addEventListener("click", async () => {
    if(InputImageElement.files.length === 0) {
        alert("ファイルを選択してください")
        return
    }
    console.log("clicked!");
    clickedElement.textContent = "処理中...";

    const fd = new FormData();
    for (const file of InputImageElement.files) {
        fd.append("files", file);
    }

    try {
        const response = await fetch("/uploads", { method: "POST", body: fd });
        if (!response.ok) {
            alert("サーバーエラー");
            return;
        }
        
        const data = await response.json();
        console.log(data);
        
        // 🚛 納品書向けの表示関数
        displayInvoiceResults(data.ocr_results);
        clickedElement.textContent = "完了!";
        
    } catch (error) {
        console.error("エラー:", error);
        clickedElement.textContent = "エラーが発生しました";
    }
});

// 🚛 納品書向けの表示関数
function displayInvoiceResults(ocrResults) {
    if (!ocrResults || ocrResults.length === 0) {
        resultElement.innerHTML = "<p style='color: #666; text-align: center; padding: 20px;'>📄 テキストが検出されませんでした</p>";
        return;
    }
    
    let html = `
        <div class="invoice-results-header">
            <h3>🚛 納品書OCR抽出結果</h3>
            <div class="results-stats">
                <span class="stat-badge">📄 ${ocrResults.length}ページ</span>
                <span class="stat-badge">📝 ${ocrResults.reduce((sum, page) => sum + page.length, 0)}個のテキスト</span>
            </div>
        </div>
    `;
    
    ocrResults.forEach((page, pageIndex) => {
        html += `
            <div class="page-section">
                <div class="page-header">
                    <h4>📄 ページ ${pageIndex + 1}</h4>
                    <span class="text-count">${page.length}個のテキスト</span>
                </div>
                
                <!-- 🎯 重要項目を上部に表示 -->
                <div class="key-items">
                    ${generateKeyItems(page)}
                </div>
                
                <!-- 📋 全テキストをカテゴリ別に表示 -->
                <div class="all-texts">
                    <h5>📋 全抽出テキスト（カテゴリ別色分け）</h5>
                    <div class="text-grid">
                        ${generateTextGrid(page)}
                    </div>
                </div>
            </div>
        `;
    });
    
    // 📊 抽出データの統計を追加
    html += generateInvoiceStatistics(ocrResults);
    
    resultElement.innerHTML = html;
}

// 🎯 重要項目を抽出・表示
function generateKeyItems(pageTexts) {
    const keyItems = {
        customer: [],      // 顧客名
        amount: [],        // 金額
        date: [],          // 日付
        tire_size: [],     // タイヤサイズ
        quantity: [],      // 数量
        work_content: []   // 作業内容
    };
    
    pageTexts.forEach(text => {
        const category = getInvoiceCategory(text);
        if (keyItems[category]) {
            keyItems[category].push(text);
        }
    });
    
    let html = '<div class="key-items-grid">';
    
    // 🎯 重要項目のみ表示
    const importantCategories = [
        { key: 'customer', label: '👤 顧客名', icon: '👤' },
        { key: 'amount', label: '💰 金額', icon: '💰' },
        { key: 'date', label: '📅 日付', icon: '📅' },
        { key: 'tire_size', label: '🚗 タイヤサイズ', icon: '🚗' },
        { key: 'quantity', label: '📦 数量', icon: '📦' },
        { key: 'work_content', label: '🔧 作業内容', icon: '🔧' }
    ];
    
    importantCategories.forEach(category => {
        const items = keyItems[category.key];
        if (items && items.length > 0) {
            html += `
                <div class="key-item-card">
                    <div class="key-item-header">
                        <span class="key-icon">${category.icon}</span>
                        <span class="key-label">${category.label}</span>
                        <span class="key-count">${items.length}</span>
                    </div>
                    <div class="key-item-values">
                        ${items.map(item => `<span class="key-value">${escapeHtml(item)}</span>`).join('')}
                    </div>
                </div>
            `;
        }
    });
    
    html += '</div>';
    return html;
}

// 📋 全テキストのグリッド表示
function generateTextGrid(pageTexts) {
    return pageTexts.map((text, index) => {
        const category = getInvoiceCategory(text);
        const categoryInfo = getInvoiceCategoryInfo(category);
        
        return `
            <div class="text-item ${category}" 
                 title="${categoryInfo.description}"
                 data-index="${index + 1}"
                 data-text="${escapeHtml(text)}">
                <span class="text-number">${index + 1}</span>
                <span class="text-content">${escapeHtml(text)}</span>
                <span class="text-category-icon">${categoryInfo.icon}</span>
            </div>
        `;
    }).join('');
}

// 🚛 納品書向けのカテゴリ判定
function getInvoiceCategory(text) {
    // 💰 金額（¥マーク、数字+円、カンマ区切り数字）
    if (/^¥?[\d,]+円?$/.test(text) || /^\d{1,3}(,\d{3})*$/.test(text)) {
        // 金額らしい数字（1000以上の数値）
        const numValue = parseInt(text.replace(/[¥,円]/g, ''));
        if (numValue >= 100) {
            return "amount";
        }
    }
    
    // 🚗 タイヤサイズ（195/65R15等の形式）
    if (/\d{3}\/\d{2}R\d{2}/.test(text) || /\d{3}[-\/]\d{2}[-\/]\d{2}/.test(text)) {
        return "tire_size";
    }
    
    // 📅 日付（年月日、スラッシュ区切り等）
    if (/\d{4}[\/\-年]\d{1,2}[\/\-月]?\d{1,2}[日]?/.test(text) || /\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}/.test(text)) {
        return "date";
    }
    
    // ⏰ 時刻
    if (/\d{1,2}[：:]\d{2}/.test(text)) {
        return "time";
    }
    
    // 📦 数量（本、個、台等の単位付き数字）
    if (/^\d+[本個台枚台数量]$/.test(text) || /^\d+\s*[本個台]$/.test(text)) {
        return "quantity";
    }
    
    // 👤 顧客名（様、株式会社、有限会社等）
    if (text.includes("様") || text.includes("株式会社") || text.includes("有限会社") || text.includes("㈱")) {
        return "customer";
    }
    
    // 🔧 作業内容（取付、交換、修理等）
    if (/取付|交換|修理|点検|整備|バランス|組替/.test(text)) {
        return "work_content";
    }
    
    // 🏪 店舗・会社情報
    if (text.includes("自動車") || text.includes("タイヤ") || text.includes("サービス") || text.includes("工場")) {
        return "shop_info";
    }
    
    // 📋 品番・型番
    if (/^[A-Z0-9\-]{5,}$/.test(text)) {
        return "product_code";
    }
    
    // 📞 電話番号
    if (/^\d{2,4}[-\(\)]\d{2,4}[-\(\)]\d{4}$/.test(text) || /^0\d{1,4}-\d{2,4}-\d{4}$/.test(text)) {
        return "phone";
    }
    
    // 📧 住所っぽいもの
    if (text.includes("県") || text.includes("市") || text.includes("区") || text.includes("町")) {
        return "address";
    }
    
    // 🔢 シンプルな数値
    if (/^\d+(\.\d+)?$/.test(text)) {
        return "number";
    }
    
    // 📝 短いテキスト
    if (text.length <= 3) {
        return "short";
    }
    
    return "other";
}

// 📋 納品書カテゴリ情報
function getInvoiceCategoryInfo(category) {
    const categoryMap = {
        "amount": { icon: "💰", description: "金額", color: "#4CAF50" },
        "tire_size": { icon: "🚗", description: "タイヤサイズ", color: "#FF5722" },
        "date": { icon: "📅", description: "日付", color: "#9C27B0" },
        "time": { icon: "⏰", description: "時刻", color: "#607D8B" },
        "quantity": { icon: "📦", description: "数量", color: "#2196F3" },
        "customer": { icon: "👤", description: "顧客名", color: "#FF9800" },
        "work_content": { icon: "🔧", description: "作業内容", color: "#795548" },
        "shop_info": { icon: "🏪", description: "店舗情報", color: "#3F51B5" },
        "product_code": { icon: "📋", description: "品番・型番", color: "#009688" },
        "phone": { icon: "📞", description: "電話番号", color: "#E91E63" },
        "address": { icon: "📧", description: "住所", color: "#8BC34A" },
        "number": { icon: "🔢", description: "数値", color: "#CDDC39" },
        "short": { icon: "📝", description: "短いテキスト", color: "#9E9E9E" },
        "other": { icon: "📄", description: "その他", color: "#757575" }
    };
    
    return categoryMap[category] || categoryMap["other"];
}

// 📊 納品書用統計情報
function generateInvoiceStatistics(ocrResults) {
    const allTexts = ocrResults.flat();
    const categories = {};
    
    allTexts.forEach(text => {
        const category = getInvoiceCategory(text);
        categories[category] = (categories[category] || 0) + 1;
    });
    
    let statsHtml = `
        <div class="invoice-statistics">
            <h4>📊 納品書データ分析</h4>
            <div class="category-breakdown">
    `;
    
    // 重要カテゴリを優先表示
    const priorityCategories = ['customer', 'amount', 'date', 'tire_size', 'quantity', 'work_content'];
    const displayedCategories = new Set();
    
    // 優先カテゴリから表示
    priorityCategories.forEach(category => {
        if (categories[category]) {
            const info = getInvoiceCategoryInfo(category);
            const count = categories[category];
            const percentage = ((count / allTexts.length) * 100).toFixed(1);
            
            statsHtml += createStatItem(info, count, percentage, true);
            displayedCategories.add(category);
        }
    });
    
    // その他のカテゴリを表示
    Object.entries(categories).forEach(([category, count]) => {
        if (!displayedCategories.has(category)) {
            const info = getInvoiceCategoryInfo(category);
            const percentage = ((count / allTexts.length) * 100).toFixed(1);
            
            statsHtml += createStatItem(info, count, percentage, false);
        }
    });
    
    statsHtml += `
            </div>
        </div>
    `;
    
    return statsHtml;
}

// 📊 統計アイテムを作成
function createStatItem(info, count, percentage, isPriority) {
    const priorityClass = isPriority ? 'priority-stat' : '';
    
    return `
        <div class="stat-item ${priorityClass}">
            <span class="stat-icon">${info.icon}</span>
            <span class="stat-label">${info.description}</span>
            <span class="stat-count">${count}個</span>
            <span class="stat-percentage">(${percentage}%)</span>
            ${isPriority ? '<span class="priority-badge">重要</span>' : ''}
        </div>
    `;
}

// HTMLエスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}