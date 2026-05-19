/**
 * Marketing Command Center - Core Logic (app.js)
 */

// ==========================================
// 1. 定数とグローバルステート
// ==========================================

const STATE = {
    currentTab: 'dashboard',
    apiKey: '',
    notionDbId: '',
    notes: [],
    history: [],
    news: []
};

// LM社標準プロンプトテンプレート
const PROMPT_TEMPLATES = {
    'lm-standard': `あなたは「LM」という共通ポイント事業を行う企業の、優秀なデータマーケティング支援パートナーAIです。
以下の前提コンテキストを踏まえ、出力フォーマットに厳密に従って、クライアント向けのマーケティング企画案を作成してください。

### 【前提コンテキスト：LM社の強みとミッション】
- あなたのミッションは、膨大なユーザー・購買データを活用し、クライアント企業のマーケティング支援をすることです。
- 顧客の課題はデータ活用、プロモーション企画、データ分析、アライアンス提携など多岐にわたります。
- 常に「LMのデータリソース（購買履歴、会員属性、ポイント利用動向など）や加盟店ネットワーク」をフル活用することを前提とし、実現性が高く、具体的でクリエイティブな戦略・施策を出力してください。
- 提供されたクライアント情報（URL/補足）を深く理解・分析した上で、的確な企画を構築してください。

### 【クライアント情報】
- 対象URL: {{URL}}
- 補足要件: {{NOTES}}

### 【出力フォーマット】
以下の1〜5の構成で、美しいMarkdown形式で出力してください。見出しは「###」から開始してください。

1. **クライアントの事業理解と課題仮説**
   - URLから読み取れる事業内容の要約と、現在抱えているであろうマーケティング上のボトルネックの推測
2. **LMデータを活用したセグメンテーション（ターゲティング）案**
   - 購買データや行動データをどう掛け合わせてターゲットを抽出するかの切り口（具体的に2〜3案）
3. **具体的なプロモーション・アプローチ施策**
   - 抽出したセグメントに対する、オウンド広告・外部データ突合広告などの具体的な配信シナリオ
4. **アライアンス（提携・協業）のアイデア**
   - LM経済圏の他の加盟店や、異業種と連携したキャンペーンの可能性
5. **施策後のデータ分析・検証の方向性**
   - 実施後にどのようなデータが得られ、どう次回に活かせるかのスキーム`,

    'wine-monetize': `あなたはワイン専門のビジネスコンサルタント、およびSommelier AIです。
クライアント（またはあなた自身のプロジェクト）のWebサイト/コンセプトを分析し、月5万円の収益を達成するためのワイン特化型ビジネスモデルとマーケティング戦略を提案してください。

### 【前提条件】
- 目標：専門知識を活かして月5万円以上の持続可能な収益をあげる。
- ターゲット：ワイン愛好家、初心者、ワインの選び方に悩むビジネスパーソン。

### 【クライアント情報】
- 対象URL: {{URL}}
- 補足要件: {{NOTES}}

### 【出力フォーマット】
以下の構成で、美しいMarkdown形式で出力してください。見出しは「###」から開始してください。

1. **ビジネスコンセプトとバリュープロポジション**
   - ターゲット顧客への独自の提供価値とコンセプト
2. **具体的なマネタイズモデル（月5万円ロードマップ）**
   - 有料メルマガ、AIソムリエ相談、デジタル教材、ワイン会など具体的な商品設計と価格設定
3. **デジタルマーケティング＆集客プラン**
   - SNS、オウンドメディア、SEOなどを活用した見込み客の獲得シナリオ
4. **アクションプラン（最初の30日間でやること）**
   - 即座に実行できるステップバイステップのタスク
5. **継続的な顧客ロイヤルティ向上策**
   - リピーターを増やすためのファンコミュニティ構築アイデア`
};

// デフォルト・ニュース（フォールバック・デモ用）
const DEFAULT_NEWS = [
    {
        title: "国内ポイント経済圏の最新トレンド：各社がマルチポイント・オープン化を加速",
        link: "https://news.google.com",
        date: "2026-05-18",
        category: "business",
        source: "仕事 (ポイント経済圏)"
    },
    {
        title: "生成AIを活用したクリエイティブ広告の自動生成ツール、主要代理店が導入開始",
        link: "https://news.google.com",
        date: "2026-05-17",
        category: "business",
        source: "仕事 (Web広告)"
    },
    {
        title: "日本ソムリエ協会、AIソムリエを活用したテイスティング支援の実証実験を開始",
        link: "https://news.google.com",
        date: "2026-05-16",
        category: "hobby",
        source: "趣味 (ワイン)"
    },
    {
        title: "Google、検索体験のアップデートを発表：AIによる概要生成がよりパーソナルに",
        link: "https://news.google.com",
        date: "2026-05-15",
        category: "hobby",
        source: "趣味 (AI)"
    }
];

// ==========================================
// 2. 初期化処理
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadNotes();
    loadHistory();
    fetchNewsFeed();
    
    // 日付表示の更新
    const dateEl = document.getElementById('date-display');
    if (dateEl) {
        const today = new Date();
        dateEl.textContent = today.toLocaleDateString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' });
    }

    // ナビゲーションのイベント登録
    document.querySelectorAll('.sidebar-nav .nav-btn, .sidebar-footer .nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
});

// ==========================================
// 3. タブ制御と表示管理
// ==========================================

function switchTab(tabId) {
    STATE.currentTab = tabId;
    
    // アクティブなナビゲーションボタンを更新
    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // アクティブなタブコンテンツを更新
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    // ヘッダータイトルの更新
    const titleEl = document.getElementById('page-title');
    const subtitleEl = document.getElementById('page-subtitle');
    
    if (titleEl && subtitleEl) {
        switch (tabId) {
            case 'dashboard':
                titleEl.textContent = 'ダッシュボード';
                subtitleEl.textContent = '今日のマーケティング活動を開始しましょう';
                break;
            case 'ai-generator':
                titleEl.textContent = 'AI企画生成';
                subtitleEl.textContent = 'Geminiのインテリジェンスでクライアント向けの最高な提案書を作成';
                break;
            case 'news-feed':
                titleEl.textContent = 'インテリジェンス';
                subtitleEl.textContent = 'あなたの設定したキーワードに基づいた最新トレンド・ニュース';
                break;
            case 'notes':
                titleEl.textContent = 'アイデア・メモ';
                subtitleEl.textContent = '業務中の気づきやひらめきをストックする';
                break;
            case 'settings':
                titleEl.textContent = '環境設定';
                subtitleEl.textContent = 'APIキーと各種連携用のアカウント設定を行います';
                break;
        }
    }
}

// ==========================================
// 4. 設定の保存・読込 (Gemini API)
// ==========================================

function loadSettings() {
    STATE.apiKey = localStorage.getItem('mcc_gemini_key') || '';
    STATE.notionDbId = localStorage.getItem('mcc_notion_db_id') || '';
    
    const keyInput = document.getElementById('gemini-key');
    const dbInput = document.getElementById('notion-db-id');
    
    if (keyInput) keyInput.value = STATE.apiKey;
    if (dbInput) dbInput.value = STATE.notionDbId;

    updateApiStatus();
}

function saveSettings(event) {
    event.preventDefault();
    const keyInput = document.getElementById('gemini-key');
    const dbInput = document.getElementById('notion-db-id');
    
    if (keyInput && dbInput) {
        STATE.apiKey = keyInput.value.trim();
        STATE.notionDbId = dbInput.value.trim();
        
        localStorage.setItem('mcc_gemini_key', STATE.apiKey);
        localStorage.setItem('mcc_notion_db_id', STATE.notionDbId);
        
        alert('設定を保存しました！');
        updateApiStatus();
        switchTab('dashboard');
    }
}

function updateApiStatus() {
    const badge = document.getElementById('api-status');
    const badgeText = document.getElementById('api-status-text');
    
    if (badge && badgeText) {
        if (STATE.apiKey) {
            badge.className = 'status-badge success';
            badgeText.textContent = 'Gemini API 接続中';
        } else {
            badge.className = 'status-badge error';
            badgeText.textContent = 'Gemini API 未設定';
        }
    }
}

// ==========================================
// 5. AI企画生成 (Gemini API 連携)
// ==========================================

async function generateMarketingPlan(event) {
    event.preventDefault();
    
    if (!STATE.apiKey) {
        alert('APIキーが設定されていません。「環境設定」タブから登録してください。');
        switchTab('settings');
        return;
    }

    const urlInput = document.getElementById('client-url').value.trim();
    const notesInput = document.getElementById('client-notes').value.trim();
    const templateKey = document.getElementById('prompt-template').value;
    const generateBtn = document.getElementById('generate-btn');
    const outputArea = document.getElementById('result-output');

    if (!urlInput) return;

    // UI Loading状態
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<div class="loading-spinner" style="margin: 0; width: 16px; height: 16px; display: inline-block;"></div> 生成中...';
    outputArea.innerHTML = `
        <div class="empty-state">
            <div class="loading-spinner"></div>
            <p>AIがクライアントURL "${urlInput}" の事業内容と強みを分析し、最適なマーケティング戦略を立案しています。これには数秒〜十数秒かかります。</p>
        </div>
    `;

    // プロンプト構築
    let prompt = PROMPT_TEMPLATES[templateKey] || PROMPT_TEMPLATES['lm-standard'];
    prompt = prompt.replace('{{URL}}', urlInput).replace('{{NOTES}}', notesInput || '特になし');

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${STATE.apiKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }]
            })
        });

        if (!response.ok) {
            throw new Error(`APIエラー: ${response.statusText}`);
        }

        const data = await response.json();
        const generatedText = data.candidates[0].content.parts[0].text;

        // 生成完了時UI処理
        renderResult(generatedText);
        
        // 履歴に追加
        saveToHistory(urlInput, templateKey, generatedText);

    } catch (error) {
        console.error(error);
        outputArea.innerHTML = `
            <div class="empty-state">
                <i data-lucide="alert-circle" style="color: var(--error-color)"></i>
                <p style="color: var(--error-color)">生成中にエラーが発生しました。<br>${error.message}</p>
            </div>
        `;
        lucide.createIcons();
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i data-lucide="play"></i> 企画案を生成する';
        lucide.createIcons();
    }
}

function renderResult(markdownText) {
    const outputArea = document.getElementById('result-output');
    const copyBtn = document.getElementById('copy-result-btn');
    
    // Markdownのレンダリング処理
    if (window.marked) {
        outputArea.innerHTML = `<div class="markdown-body">${window.marked.parse(markdownText)}</div>`;
    } else {
        // 自作簡易パーサ
        let html = markdownText
            .replace(/### (.*?)\n/g, '<h3>$1</h3>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/- (.*?)\n/g, '<li>$1</li>')
            .replace(/\n\n/g, '<br><br>');
        outputArea.innerHTML = `<div class="markdown-body">${html}</div>`;
    }
    
    if (copyBtn) copyBtn.disabled = false;
}

function copyResultToClipboard() {
    const output = document.getElementById('result-output').innerText;
    navigator.clipboard.writeText(output).then(() => {
        alert('クリップボードにコピーしました！');
    }).catch(err => {
        console.error('コピー失敗:', err);
    });
}

// ==========================================
// 6. 履歴管理 (AI企画)
// ==========================================

function loadHistory() {
    STATE.history = JSON.parse(localStorage.getItem('mcc_history')) || [];
    renderHistory();
}

function saveToHistory(url, templateKey, resultText) {
    const historyItem = {
        id: Date.now(),
        url: url,
        template: templateKey === 'lm-standard' ? 'LM社標準' : 'ワイン収益化',
        date: new Date().toLocaleDateString('ja-JP'),
        result: resultText
    };
    
    STATE.history.unshift(historyItem);
    // 最大10件まで
    if (STATE.history.length > 10) STATE.history.pop();
    
    localStorage.setItem('mcc_history', JSON.stringify(STATE.history));
    renderHistory();
}

function renderHistory() {
    const listEl = document.getElementById('quick-history-list');
    if (!listEl) return;

    if (STATE.history.length === 0) {
        listEl.innerHTML = '<p class="empty-state">まだ履歴がありません</p>';
        return;
    }

    listEl.innerHTML = STATE.history.map(item => `
        <div class="history-card" onclick="loadHistoryToPreview(${item.id})">
            <div class="history-card-header">
                <span class="history-tag">${item.template}</span>
                <span class="history-date">${item.date}</span>
            </div>
            <div class="history-url">${item.url}</div>
        </div>
    `).join('');
}

function loadHistoryToPreview(id) {
    const item = STATE.history.find(h => h.id === id);
    if (item) {
        switchTab('ai-generator');
        document.getElementById('client-url').value = item.url;
        renderResult(item.result);
    }
}

// ==========================================
// 7. ニュースフィード (インテリジェンス)
// ==========================================

async function fetchNewsFeed(forceRefresh = false) {
    const gridEl = document.getElementById('news-grid-list');
    const quickGridEl = document.getElementById('quick-news-list');
    
    if (gridEl) gridEl.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div> ニュースを同期中...</div>';

    // デフォルトデータを即表示
    STATE.news = DEFAULT_NEWS;
    renderNews();

    // 実際のRSSフィード取得（CORSプロキシ経由で非同期に取得）
    try {
        const keywords = ["マーケティング", "ポイント経済圏", "ワイン"];
        const proxyUrl = "https://api.allorigins.win/get?url=";
        const fetchedNews = [];

        for (const kw of keywords) {
            const feedUrl = encodeURIComponent(`https://news.google.com/rss/search?q=${kw}&hl=ja&gl=JP&ceid=JP:ja`);
            const response = await fetch(`${proxyUrl}${feedUrl}`);
            if (response.ok) {
                const data = await response.json();
                const parser = new DOMParser();
                const xml = parser.parseFromString(data.contents, "text/xml");
                const items = xml.querySelectorAll("item");
                
                let count = 0;
                items.forEach(item => {
                    if (count < 2) { // 各キーワードから2件ずつ
                        const title = item.querySelector("title").textContent;
                        const link = item.querySelector("link").textContent;
                        const pubDate = item.querySelector("pubDate").textContent;
                        const dateObj = new Date(pubDate);
                        
                        fetchedNews.push({
                            title: title,
                            link: link,
                            date: dateObj.toISOString().split('T')[0],
                            category: kw === 'ワイン' ? 'hobby' : 'business',
                            source: kw === 'ワイン' ? `趣味 (${kw})` : `仕事 (${kw})`
                        });
                        count++;
                    }
                });
            }
        }

        if (fetchedNews.length > 0) {
            STATE.news = fetchedNews;
            renderNews();
        }
    } catch (e) {
        console.warn("RSSのリアルタイム取得に失敗しました。ローカルデータを使用します。", e);
    }
}

function renderNews(filteredNews = null) {
    const listToRender = filteredNews || STATE.news;
    const gridEl = document.getElementById('news-grid-list');
    const quickGridEl = document.getElementById('quick-news-list');

    // 1. メインフィードの描画
    if (gridEl) {
        if (listToRender.length === 0) {
            gridEl.innerHTML = '<p class="empty-state">該当するニュースはありません</p>';
        } else {
            gridEl.innerHTML = listToRender.map(item => `
                <div class="news-card">
                    <span class="news-card-tag ${item.category}">${item.source}</span>
                    <h4>${item.title}</h4>
                    <div class="news-card-meta">
                        <span>${item.date}</span>
                        <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="btn-text">開く <i data-lucide="external-link" style="width:12px;"></i></a>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }
    }

    // 2. ダッシュボードのクイックリスト描画 (上位3件)
    if (quickGridEl) {
        const top3 = STATE.news.slice(0, 3);
        quickGridEl.innerHTML = top3.map(item => `
            <div class="quick-news-item">
                <span class="news-tag ${item.category}">${item.source}</span>
                <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="quick-news-title">${item.title}</a>
            </div>
        `).join('');
    }
}

function filterCategory(category) {
    document.querySelectorAll('.filter-chip').forEach(chip => {
        if (chip.getAttribute('data-category') === category) {
            chip.classList.add('active');
        } else {
            chip.classList.remove('active');
        }
    });

    if (category === 'all') {
        renderNews();
    } else {
        const filtered = STATE.news.filter(n => n.category === category);
        renderNews(filtered);
    }
}

function filterNews() {
    const searchVal = document.getElementById('news-search').value.toLowerCase();
    const filtered = STATE.news.filter(n => n.title.toLowerCase().includes(searchVal));
    renderNews(filtered);
}

// ==========================================
// 8. アイデア・メモ管理 (LocalStorage)
// ==========================================

function loadNotes() {
    STATE.notes = JSON.parse(localStorage.getItem('mcc_notes')) || [];
    renderNotes();
}

function saveNote(event) {
    event.preventDefault();
    const titleEl = document.getElementById('note-title');
    const contentEl = document.getElementById('note-content');
    const tagEl = document.getElementById('note-tag');

    if (titleEl && contentEl) {
        const newNote = {
            id: Date.now(),
            title: titleEl.value.trim(),
            content: contentEl.value.trim(),
            tag: tagEl.value,
            date: new Date().toLocaleDateString('ja-JP')
        };

        STATE.notes.unshift(newNote);
        localStorage.setItem('mcc_notes', JSON.stringify(STATE.notes));
        
        titleEl.value = '';
        contentEl.value = '';
        
        renderNotes();
        alert('メモを保存しました！');
    }
}

function deleteNote(id) {
    if (confirm('このメモを削除してもよろしいですか？')) {
        STATE.notes = STATE.notes.filter(note => note.id !== id);
        localStorage.setItem('mcc_notes', JSON.stringify(STATE.notes));
        renderNotes();
    }
}

function renderNotes(filteredNotes = null) {
    const listToRender = filteredNotes || STATE.notes;
    const gridEl = document.getElementById('notes-grid-display');
    if (!gridEl) return;

    if (listToRender.length === 0) {
        gridEl.innerHTML = '<p class="empty-state" style="grid-column: span 2;">メモがありません。左のフォームから作成してください。</p>';
        return;
    }

    gridEl.innerHTML = listToRender.map(note => `
        <div class="note-card">
            <span class="note-card-tag">${note.tag}</span>
            <h4>${note.title}</h4>
            <p>${note.content}</p>
            <div class="note-card-footer" style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; font-size:11px; color:var(--text-dim);">
                <span>${note.date}</span>
                <button class="btn-text" onclick="deleteNote(${note.id})" style="color:var(--error-color)">削除</button>
            </div>
        </div>
    `).join('');
}

function filterNotes() {
    const searchVal = document.getElementById('notes-search').value.toLowerCase();
    const filtered = STATE.notes.filter(note => 
        note.title.toLowerCase().includes(searchVal) || 
        note.content.toLowerCase().includes(searchVal)
    );
    renderNotes(filtered);
}
