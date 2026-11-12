/**
 * 全國語文競賽 國語字音字形（高中學生組）數位學習系統
 * 第一階段：1. 線上複習（含注音虛擬鍵盤與國字打字輸入互動模式、列表總覽模式）
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'su_word_agy_review_state_v1';

  // 注音符號槽位定義
  const ZHUYIN_INITIAL_GROUPS = [
    ['ㄅ', 'ㄆ', 'ㄇ', 'ㄈ'],
    ['ㄉ', 'ㄊ', 'ㄋ', 'ㄌ'],
    ['ㄍ', 'ㄎ', 'ㄏ', 'ㄐ', 'ㄑ', 'ㄒ'],
    ['ㄓ', 'ㄔ', 'ㄕ', 'ㄖ', 'ㄗ', 'ㄘ', 'ㄙ']
  ];
  const ZHUYIN_MEDIALS = ['ㄧ', 'ㄨ', 'ㄩ'];
  const ZHUYIN_FINAL_GROUPS = [
    ['ㄚ', 'ㄛ', 'ㄜ', 'ㄝ'],
    ['ㄞ', 'ㄟ', 'ㄠ', 'ㄡ'],
    ['ㄢ', 'ㄣ', 'ㄤ', 'ㄥ', 'ㄦ']
  ];
  const ZHUYIN_TONES = [
    { symbol: '', mark: 'ˉ', text: '一聲' },
    { symbol: 'ˊ', mark: 'ˊ', text: '二聲' },
    { symbol: 'ˇ', mark: 'ˇ', text: '三聲' },
    { symbol: 'ˋ', mark: 'ˋ', text: '四聲' },
    { symbol: '˙', mark: '˙', text: '輕聲' }
  ];

  // 應用程式狀態
  const state = {
    allQuestions: [],
    years: [],
    filteredQuestions: [],
    currentIndex: 0,
    viewMode: 'card', // 'card' | 'list'
    activeModule: 'review', // 'review' | 'quiz' | 'docx'
    filters: {
      selectedYears: new Set([101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]),
      type: 'all', // 'all' | 'pronunciation' | 'character'
      status: 'all', // 'all' | 'unpracticed' | 'wrong' | 'starred' | 'mastered'
      keyword: ''
    },
    isShuffled: false,
    autoNextOnCorrect: false,
    listMaskAll: true,
    listRevealedIds: new Set(),
    listPage: 1,
    listPageSize: 100,

    // 注音虛擬鍵盤目前槽位狀態
    zhuyinSlots: {
      initial: '',
      medial: '',
      final: '',
      tone: ''
    },

    // 使用者本機學習紀錄 (持久化於 localStorage)
    records: {
      // id -> 'mastered' | 'wrong'
      statusMap: {},
      // id -> true
      starredMap: {}
    },

    // 第二階段：線上測驗狀態
    quiz: {
      selectedYears: new Set([101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]),
      qType: 'balanced', // 'balanced' | 'pronunciation' | 'character'
      qSource: 'all', // 'all' | 'unpracticed' | 'weak'
      qCount: 20,
      timerMode: 'timed', // 'timed' | 'untimed'
      stage: 'setup', // 'setup' | 'running' | 'result'
      questions: [],
      currentIndex: 0,
      userAnswers: {}, // q.id -> string
      userZhuyinSlots: {}, // q.id -> { initial, medial, final, tone }
      startTime: 0,
      elapsedSeconds: 0,
      limitSeconds: 60,
      timerId: null,
      paletteOpen: true,
      resultFilter: 'all' // 'all' | 'wrong'
    },

    // 第三階段：紙本試卷 Word (.docx) 產生器狀態
    docx: {
      selectedYears: new Set([101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]),
      qType: 'balanced', // 'balanced' | 'pronunciation' | 'character'
      qSource: 'all', // 'all' | 'unpracticed' | 'weak'
      qCount: 100,
      title: '國立竹山高中 國語字音字形測驗卷（高中學生組）',
      paperSize: 'A4', // 'A4' | 'B4' | 'A3'
      orientation: 'landscape', // 'landscape' | 'portrait'
      textDir: 'vertical', // 'vertical' | 'horizontal'
      bracketStyle: 'corner_underline', // 'corner_underline' | 'corner_only'
      previewMode: 'student', // 'student' | 'teacher'
      sampledQuestions: []
    }
  };

  let isImeComposing = false;
  let autoNextTimer = null;

  // =========================================================================
  // 1. 初始化與資料載入
  // =========================================================================
  function loadLocalStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          state.records.statusMap = parsed.statusMap || {};
          state.records.starredMap = parsed.starredMap || {};
          state.autoNextOnCorrect = Boolean(parsed.autoNextOnCorrect);
        }
      }
    } catch (err) {
      console.warn('無法讀取本機學習紀錄：', err);
    }
  }

  function saveLocalStorage() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          statusMap: state.records.statusMap,
          starredMap: state.records.starredMap,
          autoNextOnCorrect: state.autoNextOnCorrect
        })
      );
    } catch (err) {
      console.warn('無法儲存本機學習紀錄：', err);
    }
  }

  async function loadQuestionBank() {
    if (window.SU_WORDS_BANK && Array.isArray(window.SU_WORDS_BANK.questions)) {
      return window.SU_WORDS_BANK;
    }
    const resp = await fetch('data/su_words_bank.json');
    if (!resp.ok) {
      throw new Error('無法載入題庫檔案 data/su_words_bank.json');
    }
    return await resp.json();
  }

  function getPdfPathForYear(year) {
    const y = Number(year);
    if (y === 110) {
      return 'topics/110年國語字音字形-高中.pdf';
    }
    return `topics/${y}年國語字音字形(高中).pdf`;
  }

  // =========================================================================
  // 2. 建構注音虛擬鍵盤 DOM
  // =========================================================================
  function buildVirtualKeyboard() {
    const initialContainer = document.getElementById('vk-initial-keys');
    const medialContainer = document.getElementById('vk-medial-keys');
    const finalContainer = document.getElementById('vk-final-keys');
    const toneContainer = document.getElementById('vk-tone-keys');

    initialContainer.innerHTML = '';
    ZHUYIN_INITIAL_GROUPS.forEach((group) => {
      const row = document.createElement('div');
      row.className = 'vk-keys-row';
      group.forEach((sym) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'vk-key key-initial';
        btn.dataset.slot = 'initial';
        btn.dataset.symbol = sym;
        btn.textContent = sym;
        btn.addEventListener('click', () => handleZhuyinKeyClick('initial', sym));
        row.appendChild(btn);
      });
      initialContainer.appendChild(row);
    });

    medialContainer.innerHTML = '';
    ZHUYIN_MEDIALS.forEach((sym) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'vk-key key-medial';
      btn.dataset.slot = 'medial';
      btn.dataset.symbol = sym;
      btn.textContent = sym;
      btn.addEventListener('click', () => handleZhuyinKeyClick('medial', sym));
      medialContainer.appendChild(btn);
    });

    finalContainer.innerHTML = '';
    ZHUYIN_FINAL_GROUPS.forEach((group) => {
      const row = document.createElement('div');
      row.className = 'vk-keys-row';
      group.forEach((sym) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'vk-key key-final';
        btn.dataset.slot = 'final';
        btn.dataset.symbol = sym;
        btn.textContent = sym;
        btn.addEventListener('click', () => handleZhuyinKeyClick('final', sym));
        row.appendChild(btn);
      });
      finalContainer.appendChild(row);
    });

    toneContainer.innerHTML = '';
    ZHUYIN_TONES.forEach((item) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'vk-key key-tone';
      btn.dataset.slot = 'tone';
      btn.dataset.symbol = item.symbol;
      btn.innerHTML = `<span class="tone-mark" aria-hidden="true">${item.mark}</span><span class="tone-text">${item.text}</span>`;
      btn.addEventListener('click', () => handleZhuyinKeyClick('tone', item.symbol));
      toneContainer.appendChild(btn);
    });
  }

  function handleZhuyinKeyClick(slot, symbol) {
    if (slot === 'tone') {
      state.zhuyinSlots.tone = state.zhuyinSlots.tone === symbol ? '' : symbol;
    } else {
      state.zhuyinSlots[slot] = state.zhuyinSlots[slot] === symbol ? '' : symbol;
    }
    updateZhuyinComposerUI();
  }

  function getComposedZhuyin() {
    const { initial, medial, final, tone } = state.zhuyinSlots;
    return `${initial}${medial}${final}${tone}`;
  }

  function hasAnyZhuyinBody() {
    const { initial, medial, final } = state.zhuyinSlots;
    return Boolean(initial || medial || final);
  }

  function clearZhuyinSlots() {
    state.zhuyinSlots.initial = '';
    state.zhuyinSlots.medial = '';
    state.zhuyinSlots.final = '';
    state.zhuyinSlots.tone = '';
    updateZhuyinComposerUI();
  }

  function backspaceZhuyinSlot() {
    if (state.zhuyinSlots.tone) {
      state.zhuyinSlots.tone = '';
    } else if (state.zhuyinSlots.final) {
      state.zhuyinSlots.final = '';
    } else if (state.zhuyinSlots.medial) {
      state.zhuyinSlots.medial = '';
    } else if (state.zhuyinSlots.initial) {
      state.zhuyinSlots.initial = '';
    }
    updateZhuyinComposerUI();
  }

  function updateZhuyinComposerUI() {
    const composed = getComposedZhuyin();
    const displayEl = document.getElementById('zhuyin-composed-text');

    if (!hasAnyZhuyinBody() && !state.zhuyinSlots.tone) {
      displayEl.textContent = '請點擊下方注音按鍵';
      displayEl.className = 'zhuyin-composed-placeholder';
    } else {
      displayEl.textContent = composed;
      displayEl.className = '';
    }

    // 更新槽位膠囊指示器
    const { initial, medial, final, tone } = state.zhuyinSlots;
    const elInit = document.getElementById('slot-initial');
    const elMed = document.getElementById('slot-medial');
    const elFin = document.getElementById('slot-final');
    const elTone = document.getElementById('slot-tone');

    elInit.textContent = `聲母：${initial || '-'}`;
    elInit.classList.toggle('filled', Boolean(initial));

    elMed.textContent = `介音：${medial || '-'}`;
    elMed.classList.toggle('filled', Boolean(medial));

    elFin.textContent = `韻母：${final || '-'}`;
    elFin.classList.toggle('filled', Boolean(final));

    const toneLabelMap = { '': '一聲(無號)', 'ˊ': 'ˊ 二聲', 'ˇ': 'ˇ 三聲', 'ˋ': 'ˋ 四聲', '˙': '˙ 輕聲' };
    elTone.textContent = `聲調：${toneLabelMap[tone]}`;
    elTone.classList.toggle('filled', Boolean(tone));

    // 更新鍵盤按鍵選取高亮
    document.querySelectorAll('.virtual-keyboard .vk-key').forEach((btn) => {
      const slot = btn.dataset.slot;
      const sym = btn.dataset.symbol;
      if (slot === 'tone') {
        const isDefaultFirstTone = sym === '' && state.zhuyinSlots.tone === '' && hasAnyZhuyinBody();
        const isExplicitTone = sym !== '' && state.zhuyinSlots.tone === sym;
        btn.classList.toggle('selected', isDefaultFirstTone || isExplicitTone);
      } else {
        btn.classList.toggle('selected', state.zhuyinSlots[slot] === sym);
      }
    });
  }

  // =========================================================================
  // 3. 篩選、搜尋、洗牌與統計更新
  // =========================================================================
  function updateStatsBar() {
    const total = state.allQuestions.length;
    const filtered = state.filteredQuestions.length;

    let masteredCount = 0;
    let wrongCount = 0;
    let starredCount = 0;

    Object.values(state.records.statusMap).forEach((st) => {
      if (st === 'mastered') masteredCount++;
      else if (st === 'wrong') wrongCount++;
    });

    Object.values(state.records.starredMap).forEach((v) => {
      if (v) starredCount++;
    });

    document.getElementById('stat-total').textContent = total.toLocaleString();
    document.getElementById('stat-filtered').textContent = filtered.toLocaleString();
    document.getElementById('stat-mastered').textContent = masteredCount.toLocaleString();
    document.getElementById('stat-wrong').textContent = wrongCount.toLocaleString();
    document.getElementById('stat-starred').textContent = starredCount.toLocaleString();
  }

  function buildYearChips() {
    const container = document.getElementById('filter-year-chips');
    if (!container) return;
    container.innerHTML = '';

    state.years.forEach((y) => {
      const yearNum = Number(y);
      const btn = document.createElement('button');
      btn.type = 'button';
      const isSelected = state.filters.selectedYears.has(yearNum);
      btn.className = `year-chip ${isSelected ? 'active' : ''}`;
      btn.dataset.year = String(yearNum);
      btn.setAttribute('aria-pressed', String(isSelected));
      btn.innerHTML = `<span class="year-chip-check">${isSelected ? '✓' : '+'}</span><span>${yearNum}年</span>`;
      btn.addEventListener('click', () => {
        if (state.filters.selectedYears.has(yearNum)) {
          state.filters.selectedYears.delete(yearNum);
        } else {
          state.filters.selectedYears.add(yearNum);
        }
        updateYearChipsUI();
        applyFilters();
      });
      container.appendChild(btn);
    });
    updateYearChipsUI();
  }

  function updateYearChipsUI() {
    const selectedSet = state.filters.selectedYears;
    const totalYears = state.years.length;
    const selectedArr = state.years.map(Number).filter((y) => selectedSet.has(y));
    const count = selectedArr.length;

    document.querySelectorAll('#filter-year-chips .year-chip').forEach((btn) => {
      const y = Number(btn.dataset.year);
      const isSelected = selectedSet.has(y);
      btn.classList.toggle('active', isSelected);
      btn.setAttribute('aria-pressed', String(isSelected));
      const checkSpan = btn.querySelector('.year-chip-check');
      if (checkSpan) {
        checkSpan.textContent = isSelected ? '✓' : '+';
      }
    });

    const summaryEl = document.getElementById('year-selection-summary');
    if (summaryEl) {
      const combinedTotal = count * 200;
      if (count === totalYears) {
        summaryEl.textContent = `全部 ${totalYears} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text';
      } else if (count === 0) {
        summaryEl.textContent = '尚未選擇年度（0 題，請點選下方年度進行組合）';
        summaryEl.className = 'year-summary-text empty';
      } else if (count <= 5) {
        summaryEl.textContent = `已選 ${selectedArr.join('、')} 年（${count} 個年度・共 ${combinedTotal.toLocaleString()} 題）`;
        summaryEl.className = 'year-summary-text active';
      } else {
        summaryEl.textContent = `已選 ${count} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text active';
      }
    }
  }

  function applyFilters(preserveCurrentQuestionId = null) {
    const { selectedYears, type, status, keyword } = state.filters;
    const kw = keyword.trim().toLowerCase();

    // 同步計算目前已勾選年度下，各題型的即時題數
    let yearCombinedAll = 0;
    let yearCombinedYin = 0;
    let yearCombinedXing = 0;

    state.allQuestions.forEach((q) => {
      if (selectedYears.has(Number(q.year))) {
        yearCombinedAll++;
        if (q.type === 'pronunciation') yearCombinedYin++;
        else if (q.type === 'character') yearCombinedXing++;
      }
    });

    const btnTypeAll = document.querySelector('#filter-type-group .seg-btn[data-type="all"]');
    const btnTypeYin = document.querySelector('#filter-type-group .seg-btn[data-type="pronunciation"]');
    const btnTypeXing = document.querySelector('#filter-type-group .seg-btn[data-type="character"]');
    if (btnTypeAll) btnTypeAll.textContent = `全部 (${yearCombinedAll})`;
    if (btnTypeYin) btnTypeYin.textContent = `甲、字音 (${yearCombinedYin})`;
    if (btnTypeXing) btnTypeXing.textContent = `乙、字形 (${yearCombinedXing})`;

    let list = state.allQuestions.filter((q) => {
      if (!selectedYears.has(Number(q.year))) {
        return false;
      }
      if (type !== 'all' && q.type !== type) {
        return false;
      }
      const qStatus = state.records.statusMap[q.id] || 'unpracticed';
      const isStarred = Boolean(state.records.starredMap[q.id]);

      if (status === 'unpracticed' && qStatus !== 'unpracticed') return false;
      if (status === 'mastered' && qStatus !== 'mastered') return false;
      if (status === 'wrong' && qStatus !== 'wrong') return false;
      if (status === 'starred' && !isStarred) return false;

      if (kw) {
        const matchId = q.id.toLowerCase().includes(kw);
        const matchNum = q.num_str.includes(kw);
        const matchPrompt = q.prompt.toLowerCase().includes(kw);
        const matchTarget = q.target.toLowerCase().includes(kw);
        const matchAnswer = q.answer.toLowerCase().includes(kw);
        if (!matchId && !matchNum && !matchPrompt && !matchTarget && !matchAnswer) {
          return false;
        }
      }
      return true;
    });

    if (state.isShuffled) {
      list = shuffleArray([...list]);
    }

    state.filteredQuestions = list;

    if (preserveCurrentQuestionId) {
      const idx = list.findIndex((item) => item.id === preserveCurrentQuestionId);
      state.currentIndex = idx >= 0 ? idx : 0;
    } else {
      state.currentIndex = 0;
    }

    state.listPage = 1;
    updateStatsBar();
    renderCurrentView();
  }

  function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // =========================================================================
  // 4. 畫面渲染（模式切換、單題卡片、列表總覽）
  // =========================================================================
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeRegExp(str) {
    return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function formatPromptHtml(q) {
    const safePrompt = escapeHtml(q.prompt);
    const safeTarget = escapeHtml(q.target);

    if (q.type === 'pronunciation') {
      const reg = new RegExp(escapeRegExp(safeTarget), 'g');
      return safePrompt.replace(reg, `<span class="target-char">${safeTarget}</span>`);
    } else {
      const reg = new RegExp(`\\s*${escapeRegExp(safeTarget)}\\s*`);
      return safePrompt.replace(reg, `<span class="target-phonetic">${safeTarget}</span>`);
    }
  }

  function renderCurrentView() {
    if (state.activeModule !== 'review') {
      return;
    }

    const emptyEl = document.getElementById('empty-state');
    const cardSection = document.getElementById('view-card');
    const listSection = document.getElementById('view-list');

    if (state.filteredQuestions.length === 0) {
      emptyEl.classList.remove('hidden');
      cardSection.classList.add('hidden');
      listSection.classList.add('hidden');
      return;
    }

    emptyEl.classList.add('hidden');

    if (state.viewMode === 'card') {
      cardSection.classList.remove('hidden');
      listSection.classList.add('hidden');
      renderQuestionCard();
    } else {
      cardSection.classList.add('hidden');
      listSection.classList.remove('hidden');
      renderQuestionsList();
    }
  }

  function populateJumpSelect() {
    const selectEl = document.getElementById('select-jump-q');
    const total = state.filteredQuestions.length;
    selectEl.innerHTML = '';

    // 為了效能，若題數超過 400 題，僅渲染前 300 題與目前題目附近區段，或簡潔文字
    state.filteredQuestions.forEach((q, idx) => {
      const opt = document.createElement('option');
      opt.value = String(idx);
      const shortType = q.type === 'pronunciation' ? '音' : '形';
      opt.textContent = `${q.year}年 ${shortType}${q.num_str}｜${q.prompt}`;
      selectEl.appendChild(opt);
    });
    selectEl.value = String(state.currentIndex);
  }

  function renderQuestionCard() {
    if (autoNextTimer) {
      clearTimeout(autoNextTimer);
      autoNextTimer = null;
    }

    const total = state.filteredQuestions.length;
    if (total === 0) return;
    if (state.currentIndex >= total) state.currentIndex = total - 1;
    if (state.currentIndex < 0) state.currentIndex = 0;

    const q = state.filteredQuestions[state.currentIndex];

    // 導覽列與下拉選單
    document.getElementById('card-index-label').textContent = `第 ${state.currentIndex + 1} / ${total} 題`;
    document.getElementById('btn-prev-q').disabled = state.currentIndex <= 0;
    document.getElementById('btn-next-q').disabled = state.currentIndex >= total - 1;

    const jumpSelect = document.getElementById('select-jump-q');
    if (jumpSelect.options.length !== total) {
      populateJumpSelect();
    } else {
      jumpSelect.value = String(state.currentIndex);
    }

    // 卡片標頭徽章
    document.getElementById('q-badge-year').textContent = `${q.year} 年`;
    const typeBadge = document.getElementById('q-badge-type');
    if (q.type === 'pronunciation') {
      typeBadge.textContent = '甲、字音';
      typeBadge.className = 'badge badge-type yin';
    } else {
      typeBadge.textContent = '乙、字形';
      typeBadge.className = 'badge badge-type xing';
    }
    document.getElementById('q-badge-num').textContent = `第 ${q.num_str} 題`;

    // 熟練狀態徽章
    const statusBadge = document.getElementById('q-badge-status');
    const qStatus = state.records.statusMap[q.id];
    if (qStatus === 'mastered') {
      statusBadge.textContent = '✓ 已熟練';
      statusBadge.className = 'badge badge-status mastered';
    } else if (qStatus === 'wrong') {
      statusBadge.textContent = '✗ 需加強';
      statusBadge.className = 'badge badge-status wrong';
    } else {
      statusBadge.className = 'badge badge-status hidden';
    }

    // 原卷 PDF 連結
    const pdfLink = document.getElementById('q-pdf-link');
    pdfLink.href = getPdfPathForYear(q.year);

    // 收藏按鈕
    const starBtn = document.getElementById('btn-star-q');
    const isStarred = Boolean(state.records.starredMap[q.id]);
    starBtn.innerHTML = isStarred
      ? '★ 已收藏重點<span class="kbd-hint"> (F2)</span>'
      : '☆ 收藏重點<span class="kbd-hint"> (F2)</span>';
    starBtn.classList.toggle('starred', isStarred);

    // 題目展示區
    const instructionEl = document.getElementById('q-instruction');
    const promptBoxEl = document.getElementById('q-prompt-display');
    const targetHintEl = document.getElementById('q-target-hint');

    promptBoxEl.innerHTML = formatPromptHtml(q);

    const pronArea = document.getElementById('input-area-pronunciation');
    const charArea = document.getElementById('input-area-character');
    const feedbackPanel = document.getElementById('feedback-panel');
    feedbackPanel.className = 'feedback-panel hidden';

    if (q.type === 'pronunciation') {
      instructionEl.textContent = '請使用下方「注音虛擬鍵盤」拼出標示字之標準注音：';
      targetHintEl.innerHTML = `測驗字：<strong id="q-target-text">${escapeHtml(q.target)}</strong>`;
      pronArea.classList.remove('hidden');
      charArea.classList.add('hidden');
      clearZhuyinSlots();
    } else {
      instructionEl.textContent = '請在下方輸入框打出標示注音所對應之「標準國字」：';
      targetHintEl.innerHTML = `測驗注音：<strong id="q-target-text">${escapeHtml(q.target)}</strong>`;
      pronArea.classList.add('hidden');
      charArea.classList.remove('hidden');
      const charInput = document.getElementById('char-answer-input');
      charInput.value = '';
      if (window.innerWidth > 768) {
        setTimeout(() => charInput.focus(), 30);
      }
    }
  }

  // =========================================================================
  // 5. 作答驗證與答案揭曉
  // =========================================================================
  function getFullCompletedPhrase(q) {
    if (q.type === 'pronunciation') {
      return `${q.prompt}（${q.target}：${q.answer}）`;
    } else {
      const reg = new RegExp(`\\s*${escapeRegExp(q.target)}\\s*`);
      const replaced = q.prompt.replace(reg, q.answer);
      return `${replaced}（${q.target} → ${q.answer}）`;
    }
  }

  function showFeedback(q, mode, userAnswer) {
    const panel = document.getElementById('feedback-panel');
    const badge = document.getElementById('feedback-badge');
    const correctEl = document.getElementById('fb-correct-ans');
    const userWrap = document.getElementById('fb-user-wrap');
    const userEl = document.getElementById('fb-user-ans');
    const fullPhraseEl = document.getElementById('fb-full-phrase');

    correctEl.textContent = q.answer;
    fullPhraseEl.textContent = getFullCompletedPhrase(q);

    if (mode === 'correct') {
      panel.className = 'feedback-panel correct';
      badge.textContent = '✓ 答對了！';
      userWrap.classList.remove('hidden');
      userEl.textContent = userAnswer;
      setQuestionStatus(q.id, 'mastered');

      if (state.autoNextOnCorrect && state.currentIndex < state.filteredQuestions.length - 1) {
        autoNextTimer = setTimeout(() => {
          goNextQuestion();
        }, 900);
      }
    } else if (mode === 'wrong') {
      panel.className = 'feedback-panel wrong';
      badge.textContent = '✗ 答錯了';
      userWrap.classList.remove('hidden');
      userEl.textContent = userAnswer || '（未作答）';
      setQuestionStatus(q.id, 'wrong');
    } else {
      panel.className = 'feedback-panel reveal';
      badge.textContent = '👁 標準答案';
      userWrap.classList.add('hidden');
    }

    scrollBelowHeader(panel);
  }

  function scrollBelowHeader(el) {
    if (!el || window.innerWidth > 768) return;
    window.requestAnimationFrame(() => {
      const header = document.getElementById('site-header');
      const headerH = header ? header.offsetHeight : 0;
      const rect = el.getBoundingClientRect();
      const fullyVisible = rect.top >= headerH + 4 && rect.bottom <= window.innerHeight - 8;
      if (fullyVisible) return;
      const top = rect.top + window.pageYOffset - headerH - 8;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    });
  }

  function checkPronunciationAnswer() {
    const q = state.filteredQuestions[state.currentIndex];
    if (!q || q.type !== 'pronunciation') return;

    const userAns = getComposedZhuyin().trim();
    if (!userAns) {
      alert('請先用注音虛擬鍵盤組合答案，或點擊「👁 看答案」直接檢視解答。');
      return;
    }

    if (userAns === q.answer) {
      showFeedback(q, 'correct', userAns);
    } else {
      showFeedback(q, 'wrong', userAns);
    }
  }

  function checkCharacterAnswer() {
    const q = state.filteredQuestions[state.currentIndex];
    if (!q || q.type !== 'character') return;

    const inputEl = document.getElementById('char-answer-input');
    const userAns = inputEl.value.trim();
    if (!userAns) {
      alert('請先在輸入框輸入國字，或點擊「👁 看答案」直接檢視解答。');
      inputEl.focus();
      return;
    }

    if (userAns === q.answer) {
      showFeedback(q, 'correct', userAns);
    } else {
      showFeedback(q, 'wrong', userAns);
    }
  }

  function revealCurrentAnswer() {
    const q = state.filteredQuestions[state.currentIndex];
    if (!q) return;
    showFeedback(q, 'reveal', '');
  }

  function setQuestionStatus(qId, status) {
    if (!status) {
      delete state.records.statusMap[qId];
    } else {
      state.records.statusMap[qId] = status;
    }
    saveLocalStorage();
    updateStatsBar();

    // 更新卡片上的狀態徽章
    const currentQ = state.filteredQuestions[state.currentIndex];
    if (currentQ && currentQ.id === qId) {
      const statusBadge = document.getElementById('q-badge-status');
      if (status === 'mastered') {
        statusBadge.textContent = '✓ 已熟練';
        statusBadge.className = 'badge badge-status mastered';
      } else if (status === 'wrong') {
        statusBadge.textContent = '✗ 需加強';
        statusBadge.className = 'badge badge-status wrong';
      } else {
        statusBadge.className = 'badge badge-status hidden';
      }
    }
  }

  function toggleStarQuestion(qId) {
    if (state.records.starredMap[qId]) {
      delete state.records.starredMap[qId];
    } else {
      state.records.starredMap[qId] = true;
    }
    saveLocalStorage();
    updateStatsBar();

    const currentQ = state.filteredQuestions[state.currentIndex];
    if (currentQ && currentQ.id === qId && state.viewMode === 'card') {
      const starBtn = document.getElementById('btn-star-q');
      const isStarred = Boolean(state.records.starredMap[qId]);
      starBtn.innerHTML = isStarred
        ? '★ 已收藏重點<span class="kbd-hint"> (F2)</span>'
        : '☆ 收藏重點<span class="kbd-hint"> (F2)</span>';
      starBtn.classList.toggle('starred', isStarred);
    }
    if (state.viewMode === 'list') {
      renderQuestionsList();
    }
  }

  function goPrevQuestion() {
    if (state.currentIndex > 0) {
      state.currentIndex--;
      renderQuestionCard();
      scrollBelowHeader(document.getElementById('q-prompt-area'));
    }
  }

  function goNextQuestion() {
    if (state.currentIndex < state.filteredQuestions.length - 1) {
      state.currentIndex++;
      renderQuestionCard();
      scrollBelowHeader(document.getElementById('q-prompt-area'));
    }
  }

  // =========================================================================
  // 6. 模式 B：題庫列表總覽渲染
  // =========================================================================
  function renderQuestionsList() {
    const total = state.filteredQuestions.length;
    const pageSize = state.listPageSize;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (state.listPage > totalPages) state.listPage = totalPages;
    if (state.listPage < 1) state.listPage = 1;

    const startIdx = (state.listPage - 1) * pageSize;
    const pageItems = state.filteredQuestions.slice(startIdx, startIdx + pageSize);

    document.getElementById('page-info-label').textContent = `${state.listPage} / ${totalPages} 頁`;
    document.getElementById('page-info-label-bottom').textContent = `第 ${state.listPage} / ${totalPages} 頁（共 ${total} 題）`;

    const disablePrev = state.listPage <= 1;
    const disableNext = state.listPage >= totalPages;
    document.getElementById('btn-page-prev').disabled = disablePrev;
    document.getElementById('btn-page-prev-bottom').disabled = disablePrev;
    document.getElementById('btn-page-next').disabled = disableNext;
    document.getElementById('btn-page-next-bottom').disabled = disableNext;

    const maskBtn = document.getElementById('btn-toggle-all-answers');
    maskBtn.textContent = state.listMaskAll
      ? '👁 全部顯示答案（目前為遮罩模式）'
      : '🙈 全部遮罩答案（目前為顯示模式）';

    const tbody = document.getElementById('questions-table-body');
    tbody.innerHTML = '';

    pageItems.forEach((q, offset) => {
      const globalIdx = startIdx + offset;
      const tr = document.createElement('tr');

      const isStarred = Boolean(state.records.starredMap[q.id]);
      const qStatus = state.records.statusMap[q.id];
      const isMasked = state.listMaskAll && !state.listRevealedIds.has(q.id);

      let statusHtml = '<span style="color:#87908b;font-size:0.82rem;">未練習</span>';
      if (qStatus === 'mastered') {
        statusHtml = '<span class="badge badge-status mastered">✓ 已熟練</span>';
      } else if (qStatus === 'wrong') {
        statusHtml = '<span class="badge badge-status wrong">✗ 需加強</span>';
      }

      const typeBadgeHtml =
        q.type === 'pronunciation'
          ? '<span class="badge badge-type yin">字音</span>'
          : '<span class="badge badge-type xing">字形</span>';

      tr.innerHTML = `
        <td class="col-star" data-label="收藏">
          <button type="button" class="star-cell-btn ${isStarred ? 'starred' : ''}" data-star-id="${q.id}" title="加入或取消重點收藏">
            ${isStarred ? '★' : '☆'}
          </button>
        </td>
        <td class="col-year" data-label="年度"><strong>${q.year}</strong></td>
        <td class="col-type" data-label="題型">${typeBadgeHtml}</td>
        <td class="col-num" data-label="題號">${q.num_str}</td>
        <td class="col-prompt" data-label="題目">${formatPromptHtml(q)}</td>
        <td class="col-target" data-label="目標">${escapeHtml(q.target)}</td>
        <td class="col-answer" data-label="解答">
          <span class="answer-mask-cell ${isMasked ? 'masked' : ''}" data-ans-id="${q.id}" title="點擊切換顯示/遮罩答案">
            ${escapeHtml(q.answer)}
          </span>
        </td>
        <td class="col-status" data-label="狀態">${statusHtml}</td>
        <td class="col-action" data-label="操作">
          <button type="button" class="btn-outline btn-sm" data-practice-idx="${globalIdx}">
            🎯 練習
          </button>
        </td>
      `;

      tbody.appendChild(tr);
    });
  }

  // =========================================================================
  // 6-B. 第二階段：2. 線上測驗模組 (MVP)
  // =========================================================================
  function buildQuizYearChips() {
    const container = document.getElementById('quiz-year-chips');
    if (!container) return;
    container.innerHTML = '';

    state.years.forEach((y) => {
      const yearNum = Number(y);
      const btn = document.createElement('button');
      btn.type = 'button';
      const isSelected = state.quiz.selectedYears.has(yearNum);
      btn.className = `year-chip ${isSelected ? 'active' : ''}`;
      btn.dataset.year = String(yearNum);
      btn.setAttribute('aria-pressed', String(isSelected));
      btn.innerHTML = `<span class="year-chip-check">${isSelected ? '✓' : '+'}</span><span>${yearNum}年</span>`;
      btn.addEventListener('click', () => {
        if (state.quiz.selectedYears.has(yearNum)) {
          state.quiz.selectedYears.delete(yearNum);
        } else {
          state.quiz.selectedYears.add(yearNum);
        }
        updateQuizSetupUI();
      });
      container.appendChild(btn);
    });
    updateQuizSetupUI();
  }

  function buildQuizVirtualKeyboard() {
    const initialContainer = document.getElementById('quiz-vk-initial-keys');
    const medialContainer = document.getElementById('quiz-vk-medial-keys');
    const finalContainer = document.getElementById('quiz-vk-final-keys');
    const toneContainer = document.getElementById('quiz-vk-tone-keys');
    if (!initialContainer) return;

    initialContainer.innerHTML = '';
    ZHUYIN_INITIAL_GROUPS.forEach((group) => {
      const row = document.createElement('div');
      row.className = 'vk-keys-row';
      group.forEach((sym) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'vk-key key-initial';
        btn.dataset.slot = 'initial';
        btn.dataset.symbol = sym;
        btn.textContent = sym;
        btn.addEventListener('click', () => handleQuizZhuyinKeyClick('initial', sym));
        row.appendChild(btn);
      });
      initialContainer.appendChild(row);
    });

    medialContainer.innerHTML = '';
    ZHUYIN_MEDIALS.forEach((sym) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'vk-key key-medial';
      btn.dataset.slot = 'medial';
      btn.dataset.symbol = sym;
      btn.textContent = sym;
      btn.addEventListener('click', () => handleQuizZhuyinKeyClick('medial', sym));
      medialContainer.appendChild(btn);
    });

    finalContainer.innerHTML = '';
    ZHUYIN_FINAL_GROUPS.forEach((group) => {
      const row = document.createElement('div');
      row.className = 'vk-keys-row';
      group.forEach((sym) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'vk-key key-final';
        btn.dataset.slot = 'final';
        btn.dataset.symbol = sym;
        btn.textContent = sym;
        btn.addEventListener('click', () => handleQuizZhuyinKeyClick('final', sym));
        row.appendChild(btn);
      });
      finalContainer.appendChild(row);
    });

    toneContainer.innerHTML = '';
    ZHUYIN_TONES.forEach((item) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'vk-key key-tone';
      btn.dataset.slot = 'tone';
      btn.dataset.symbol = item.symbol;
      btn.innerHTML = `<span class="tone-mark" aria-hidden="true">${item.mark}</span><span class="tone-text">${item.text}</span>`;
      btn.addEventListener('click', () => handleQuizZhuyinKeyClick('tone', item.symbol));
      toneContainer.appendChild(btn);
    });
  }

  function getQuizCandidatePools() {
    const { selectedYears, qSource } = state.quiz;
    const yearQuestions = state.allQuestions.filter((q) => selectedYears.has(Number(q.year)));

    let primaryYin = [];
    let primaryXing = [];
    let fallbackYin = [];
    let fallbackXing = [];

    yearQuestions.forEach((q) => {
      const qStatus = state.records.statusMap[q.id] || 'unpracticed';
      const isStarred = Boolean(state.records.starredMap[q.id]);

      if (qSource === 'weak') {
        if (qStatus === 'wrong' || isStarred) {
          if (q.type === 'pronunciation') primaryYin.push(q);
          else primaryXing.push(q);
        }
      } else if (qSource === 'unpracticed') {
        if (qStatus === 'unpracticed') {
          if (q.type === 'pronunciation') primaryYin.push(q);
          else primaryXing.push(q);
        } else {
          if (q.type === 'pronunciation') fallbackYin.push(q);
          else fallbackXing.push(q);
        }
      } else {
        if (q.type === 'pronunciation') primaryYin.push(q);
        else primaryXing.push(q);
      }
    });

    return { primaryYin, primaryXing, fallbackYin, fallbackXing };
  }

  function formatSecondsMMSS(sec) {
    const s = Math.max(0, Math.floor(sec));
    const mm = String(Math.floor(s / 60)).padStart(2, '0');
    const ss = String(s % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  }

  function updateQuizSetupUI() {
    const selectedSet = state.quiz.selectedYears;
    const totalYears = state.years.length;
    const selectedArr = state.years.map(Number).filter((y) => selectedSet.has(y));
    const count = selectedArr.length;

    document.querySelectorAll('#quiz-year-chips .year-chip').forEach((btn) => {
      const y = Number(btn.dataset.year);
      const isSelected = selectedSet.has(y);
      btn.classList.toggle('active', isSelected);
      btn.setAttribute('aria-pressed', String(isSelected));
      const checkSpan = btn.querySelector('.year-chip-check');
      if (checkSpan) checkSpan.textContent = isSelected ? '✓' : '+';
    });

    const summaryEl = document.getElementById('quiz-year-summary');
    if (summaryEl) {
      const combinedTotal = count * 200;
      if (count === totalYears) {
        summaryEl.textContent = `全部 ${totalYears} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text';
      } else if (count === 0) {
        summaryEl.textContent = '尚未選擇年度（請點選下方年度）';
        summaryEl.className = 'year-summary-text empty';
      } else if (count <= 5) {
        summaryEl.textContent = `已選 ${selectedArr.join('、')} 年（${count} 個年度・共 ${combinedTotal.toLocaleString()} 題）`;
        summaryEl.className = 'year-summary-text active';
      } else {
        summaryEl.textContent = `已選 ${count} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text active';
      }
    }

    const { primaryYin, primaryXing, fallbackYin, fallbackXing } = getQuizCandidatePools();
    const { qType, qCount, timerMode } = state.quiz;

    let availYin = primaryYin.length + fallbackYin.length;
    let availXing = primaryXing.length + fallbackXing.length;
    let poolTotal = 0;
    let drawYin = 0;
    let drawXing = 0;

    if (qType === 'pronunciation') {
      poolTotal = primaryYin.length;
      drawYin = Math.min(qCount, availYin);
    } else if (qType === 'character') {
      poolTotal = primaryXing.length;
      drawXing = Math.min(qCount, availXing);
    } else {
      poolTotal = primaryYin.length + primaryXing.length;
      const half = Math.floor(qCount / 2);
      drawYin = Math.min(half, availYin);
      drawXing = Math.min(qCount - drawYin, availXing);
      if (drawYin + drawXing < qCount) {
        const rem = qCount - (drawYin + drawXing);
        if (availYin > drawYin) {
          drawYin += Math.min(rem, availYin - drawYin);
        } else if (availXing > drawXing) {
          drawXing += Math.min(rem, availXing - drawXing);
        }
      }
    }

    const totalDraw = drawYin + drawXing;
    const limitSec = Math.max(30, Math.round((totalDraw / 20) * 60));
    const timerDesc = timerMode === 'timed' ? formatSecondsMMSS(limitSec) : '不限時';

    const statusEl = document.getElementById('quiz-pool-status');
    const startBtn = document.getElementById('btn-start-quiz');
    if (statusEl) {
      statusEl.innerHTML = `符合條件題池：<strong>${poolTotal.toLocaleString()}</strong> 題｜預計抽出：<strong>${totalDraw}</strong> 題（字音 ${drawYin} 題、字形 ${drawXing} 題）｜限時：<strong>${timerDesc}</strong>`;
    }
    if (startBtn) {
      startBtn.disabled = totalDraw === 0;
    }
  }

  function renderQuizStage() {
    const setupView = document.getElementById('quiz-setup-view');
    const runnerView = document.getElementById('quiz-runner-view');
    const resultView = document.getElementById('quiz-result-view');

    setupView.classList.toggle('hidden', state.quiz.stage !== 'setup');
    runnerView.classList.toggle('hidden', state.quiz.stage !== 'running');
    resultView.classList.toggle('hidden', state.quiz.stage !== 'result');

    if (state.quiz.stage === 'setup') {
      updateQuizSetupUI();
    } else if (state.quiz.stage === 'running') {
      renderQuizRunner();
    } else if (state.quiz.stage === 'result') {
      renderQuizResult();
    }
  }

  function startQuiz() {
    const { primaryYin, primaryXing, fallbackYin, fallbackXing } = getQuizCandidatePools();
    const { qType, qCount, timerMode } = state.quiz;

    const sampleFromPool = (prim, fall, needed) => {
      const sPrim = shuffleArray([...prim]);
      if (sPrim.length >= needed) {
        return sPrim.slice(0, needed);
      }
      const sFall = shuffleArray([...fall]);
      return [...sPrim, ...sFall.slice(0, needed - sPrim.length)];
    };

    const availYin = primaryYin.length + fallbackYin.length;
    const availXing = primaryXing.length + fallbackXing.length;

    let chosenYin = [];
    let chosenXing = [];

    if (qType === 'pronunciation') {
      chosenYin = sampleFromPool(primaryYin, fallbackYin, Math.min(qCount, availYin));
    } else if (qType === 'character') {
      chosenXing = sampleFromPool(primaryXing, fallbackXing, Math.min(qCount, availXing));
    } else {
      const half = Math.floor(qCount / 2);
      let dYin = Math.min(half, availYin);
      let dXing = Math.min(qCount - dYin, availXing);
      if (dYin + dXing < qCount) {
        const rem = qCount - (dYin + dXing);
        if (availYin > dYin) dYin += Math.min(rem, availYin - dYin);
        else if (availXing > dXing) dXing += Math.min(rem, availXing - dXing);
      }
      chosenYin = sampleFromPool(primaryYin, fallbackYin, dYin);
      chosenXing = sampleFromPool(primaryXing, fallbackXing, dXing);
    }

    const quizQuestions = [...chosenYin, ...chosenXing];
    if (quizQuestions.length === 0) {
      alert('目前選擇的條件下沒有可抽出的題目，請勾選更多年度或改選「全部隨機抽題」。');
      return;
    }

    stopQuizTimer();
    state.quiz.questions = quizQuestions;
    state.quiz.currentIndex = 0;
    state.quiz.userAnswers = {};
    state.quiz.userZhuyinSlots = {};
    state.quiz.startTime = Date.now();
    state.quiz.elapsedSeconds = 0;
    state.quiz.limitSeconds = Math.max(30, Math.round((quizQuestions.length / 20) * 60));
    state.quiz.paletteOpen = window.innerWidth > 768;
    state.quiz.stage = 'running';

    const palettePanel = document.getElementById('quiz-palette-panel');
    const paletteBtn = document.getElementById('btn-quiz-toggle-palette');
    if (palettePanel && paletteBtn) {
      palettePanel.classList.toggle('hidden', !state.quiz.paletteOpen);
      paletteBtn.textContent = state.quiz.paletteOpen ? '🔢 題號導覽 ▴' : '🔢 題號導覽 ▾';
    }

    renderQuizStage();
    updateQuizTimerDisplay();

    state.quiz.timerId = setInterval(() => {
      state.quiz.elapsedSeconds = Math.floor((Date.now() - state.quiz.startTime) / 1000);
      updateQuizTimerDisplay();
      if (timerMode === 'timed' && state.quiz.elapsedSeconds >= state.quiz.limitSeconds) {
        submitQuiz(true);
      }
    }, 500);
  }

  function stopQuizTimer() {
    if (state.quiz.timerId) {
      clearInterval(state.quiz.timerId);
      state.quiz.timerId = null;
    }
  }

  function updateQuizTimerDisplay() {
    const badge = document.getElementById('quiz-timer-badge');
    if (!badge) return;
    if (state.quiz.timerMode === 'timed') {
      const rem = Math.max(0, state.quiz.limitSeconds - state.quiz.elapsedSeconds);
      badge.textContent = `⏱ 剩餘 ${formatSecondsMMSS(rem)}`;
      badge.classList.toggle('danger', rem <= 30);
    } else {
      badge.textContent = `⏱ 用時 ${formatSecondsMMSS(state.quiz.elapsedSeconds)}`;
      badge.classList.remove('danger');
    }
  }

  function getQuizSlotsForQuestion(qId) {
    if (!state.quiz.userZhuyinSlots[qId]) {
      state.quiz.userZhuyinSlots[qId] = { initial: '', medial: '', final: '', tone: '' };
    }
    return state.quiz.userZhuyinSlots[qId];
  }

  function handleQuizZhuyinKeyClick(slot, symbol) {
    const q = state.quiz.questions[state.quiz.currentIndex];
    if (!q || q.type !== 'pronunciation') return;
    const slots = getQuizSlotsForQuestion(q.id);
    slots[slot] = slots[slot] === symbol ? '' : symbol;
    syncQuizPronunciationAnswer(q.id);
    updateQuizZhuyinComposerUI(q.id);
    updateQuizProgressAndPalette();
  }

  function syncQuizPronunciationAnswer(qId) {
    const slots = getQuizSlotsForQuestion(qId);
    const hasBody = Boolean(slots.initial || slots.medial || slots.final);
    if (!hasBody && !slots.tone) {
      delete state.quiz.userAnswers[qId];
    } else {
      state.quiz.userAnswers[qId] = `${slots.initial}${slots.medial}${slots.final}${slots.tone}`;
    }
  }

  function clearQuizCurrentQuestionInput() {
    const q = state.quiz.questions[state.quiz.currentIndex];
    if (!q) return;
    if (q.type === 'pronunciation') {
      state.quiz.userZhuyinSlots[q.id] = { initial: '', medial: '', final: '', tone: '' };
      delete state.quiz.userAnswers[q.id];
      updateQuizZhuyinComposerUI(q.id);
    } else {
      const inp = document.getElementById('quiz-char-answer-input');
      if (inp) inp.value = '';
      delete state.quiz.userAnswers[q.id];
    }
    updateQuizProgressAndPalette();
  }

  function backspaceQuizZhuyinSlot() {
    const q = state.quiz.questions[state.quiz.currentIndex];
    if (!q || q.type !== 'pronunciation') return;
    const slots = getQuizSlotsForQuestion(q.id);
    if (slots.tone) slots.tone = '';
    else if (slots.final) slots.final = '';
    else if (slots.medial) slots.medial = '';
    else if (slots.initial) slots.initial = '';
    syncQuizPronunciationAnswer(q.id);
    updateQuizZhuyinComposerUI(q.id);
    updateQuizProgressAndPalette();
  }

  function updateQuizZhuyinComposerUI(qId) {
    const slots = getQuizSlotsForQuestion(qId);
    const hasBody = Boolean(slots.initial || slots.medial || slots.final);
    const composed = `${slots.initial}${slots.medial}${slots.final}${slots.tone}`;
    const displayEl = document.getElementById('quiz-zhuyin-composed-text');

    if (!hasBody && !slots.tone) {
      displayEl.textContent = '請點擊下方注音按鍵';
      displayEl.className = 'zhuyin-composed-placeholder';
    } else {
      displayEl.textContent = composed;
      displayEl.className = '';
    }

    const elInit = document.getElementById('quiz-slot-initial');
    const elMed = document.getElementById('quiz-slot-medial');
    const elFin = document.getElementById('quiz-slot-final');
    const elTone = document.getElementById('quiz-slot-tone');

    elInit.textContent = `聲母：${slots.initial || '-'}`;
    elInit.classList.toggle('filled', Boolean(slots.initial));
    elMed.textContent = `介音：${slots.medial || '-'}`;
    elMed.classList.toggle('filled', Boolean(slots.medial));
    elFin.textContent = `韻母：${slots.final || '-'}`;
    elFin.classList.toggle('filled', Boolean(slots.final));

    const toneLabelMap = { '': '一聲(無號)', 'ˊ': 'ˊ 二聲', 'ˇ': 'ˇ 三聲', 'ˋ': 'ˋ 四聲', '˙': '˙ 輕聲' };
    elTone.textContent = `聲調：${toneLabelMap[slots.tone]}`;
    elTone.classList.toggle('filled', Boolean(slots.tone));

    document.querySelectorAll('#quiz-input-pronunciation .virtual-keyboard .vk-key').forEach((btn) => {
      const slot = btn.dataset.slot;
      const sym = btn.dataset.symbol;
      if (slot === 'tone') {
        const isDefaultFirstTone = sym === '' && slots.tone === '' && hasBody;
        const isExplicitTone = sym !== '' && slots.tone === sym;
        btn.classList.toggle('selected', isDefaultFirstTone || isExplicitTone);
      } else {
        btn.classList.toggle('selected', slots[slot] === sym);
      }
    });
  }

  function updateQuizProgressAndPalette() {
    const total = state.quiz.questions.length;
    let answeredCount = 0;
    state.quiz.questions.forEach((q) => {
      if ((state.quiz.userAnswers[q.id] || '').trim() !== '') {
        answeredCount++;
      }
    });

    const progEl = document.getElementById('quiz-answered-progress');
    if (progEl) {
      progEl.textContent = `已作答 ${answeredCount} / ${total} 題`;
    }

    const currQ = state.quiz.questions[state.quiz.currentIndex];
    const savedInd = document.getElementById('quiz-saved-indicator');
    if (savedInd && currQ) {
      const ans = (state.quiz.userAnswers[currQ.id] || '').trim();
      if (ans) {
        savedInd.textContent = `✓ 已填入：${ans}`;
        savedInd.className = 'quiz-saved-indicator answered';
      } else {
        savedInd.textContent = '尚未作答';
        savedInd.className = 'quiz-saved-indicator';
      }
    }

    const gridEl = document.getElementById('quiz-palette-grid');
    if (!gridEl) return;

    if (gridEl.children.length !== total) {
      gridEl.innerHTML = '';
      state.quiz.questions.forEach((q, idx) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'palette-num-btn';
        btn.textContent = String(idx + 1);
        btn.addEventListener('click', () => {
          state.quiz.currentIndex = idx;
          renderQuizRunner();
        });
        gridEl.appendChild(btn);
      });
    }

    Array.from(gridEl.children).forEach((btn, idx) => {
      const q = state.quiz.questions[idx];
      const hasAns = Boolean((state.quiz.userAnswers[q.id] || '').trim());
      btn.classList.toggle('current', idx === state.quiz.currentIndex);
      btn.classList.toggle('answered', hasAns);
    });
  }

  function renderQuizRunner() {
    const total = state.quiz.questions.length;
    if (total === 0) return;
    if (state.quiz.currentIndex >= total) state.quiz.currentIndex = total - 1;
    if (state.quiz.currentIndex < 0) state.quiz.currentIndex = 0;

    const idx = state.quiz.currentIndex;
    const q = state.quiz.questions[idx];

    document.getElementById('quiz-q-seq').textContent = `第 ${idx + 1} / ${total} 題`;
    document.getElementById('quiz-q-year').textContent = `${q.year} 年`;

    const typeBadge = document.getElementById('quiz-q-type');
    if (q.type === 'pronunciation') {
      typeBadge.textContent = '甲、字音';
      typeBadge.className = 'badge badge-type yin';
    } else {
      typeBadge.textContent = '乙、字形';
      typeBadge.className = 'badge badge-type xing';
    }
    document.getElementById('quiz-q-num').textContent = `原卷第 ${q.num_str} 題`;

    document.getElementById('quiz-prompt-display').innerHTML = formatPromptHtml(q);

    const pronZone = document.getElementById('quiz-input-pronunciation');
    const charZone = document.getElementById('quiz-input-character');
    const instEl = document.getElementById('quiz-q-instruction');
    const targetHintEl = document.getElementById('quiz-target-hint');

    if (q.type === 'pronunciation') {
      instEl.textContent = '請使用下方「注音虛擬鍵盤」拼出標示字之標準注音（點選按鍵即自動記錄本題作答）：';
      targetHintEl.innerHTML = `測驗字：<strong id="quiz-target-text">${escapeHtml(q.target)}</strong>`;
      pronZone.classList.remove('hidden');
      charZone.classList.add('hidden');
      updateQuizZhuyinComposerUI(q.id);
    } else {
      instEl.textContent = '請在下方輸入框打出標示注音所對應之「標準國字」（輸入即自動記錄本題作答）：';
      targetHintEl.innerHTML = `測驗注音：<strong id="quiz-target-text">${escapeHtml(q.target)}</strong>`;
      pronZone.classList.add('hidden');
      charZone.classList.remove('hidden');
      const charInput = document.getElementById('quiz-char-answer-input');
      charInput.value = state.quiz.userAnswers[q.id] || '';
      if (window.innerWidth > 768) {
        setTimeout(() => charInput.focus(), 30);
      }
    }

    document.getElementById('btn-quiz-prev').disabled = idx <= 0;
    const nextBtn = document.getElementById('btn-quiz-next');
    nextBtn.disabled = idx >= total - 1;

    const isLast = idx === total - 1;
    const nextActionLabel = isLast
      ? '📤 完成並交卷結算<span class="kbd-hint"> (Enter)</span>'
      : '確認並下一題<span class="kbd-hint"> (Enter)</span> ▶';
    document.getElementById('btn-quiz-zhuyin-next').innerHTML = nextActionLabel;
    document.getElementById('btn-quiz-char-next').innerHTML = nextActionLabel;

    updateQuizProgressAndPalette();
  }

  function advanceOrSubmitQuizQuestion() {
    const total = state.quiz.questions.length;
    if (state.quiz.currentIndex < total - 1) {
      state.quiz.currentIndex++;
      renderQuizRunner();
      scrollBelowHeader(document.getElementById('quiz-prompt-area'));
    } else {
      requestSubmitQuiz();
    }
  }

  function requestSubmitQuiz() {
    const total = state.quiz.questions.length;
    let unansweredCount = 0;
    state.quiz.questions.forEach((q) => {
      if ((state.quiz.userAnswers[q.id] || '').trim() === '') {
        unansweredCount++;
      }
    });

    if (unansweredCount > 0) {
      if (!confirm(`您還有 ${unansweredCount} 題尚未作答，確定要現在交卷結算嗎？`)) {
        return;
      }
    }
    submitQuiz(false);
  }

  function submitQuiz(isAutoTimeout = false) {
    stopQuizTimer();
    state.quiz.elapsedSeconds = Math.floor((Date.now() - state.quiz.startTime) / 1000);

    if (isAutoTimeout) {
      alert('⏰ 測驗時間到！系統已自動為您交卷並計算成績。');
    }

    // 批改並自動更新本機學習紀錄
    state.quiz.questions.forEach((q) => {
      const userAns = (state.quiz.userAnswers[q.id] || '').trim();
      const isCorrect = userAns === q.answer;
      state.records.statusMap[q.id] = isCorrect ? 'mastered' : 'wrong';
    });
    saveLocalStorage();
    updateStatsBar();

    state.quiz.resultFilter = 'all';
    document.querySelectorAll('#quiz-res-filter-group .seg-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.rfilter === 'all');
    });

    state.quiz.stage = 'result';
    renderQuizStage();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderQuizResult() {
    const questions = state.quiz.questions;
    const total = questions.length;
    if (total === 0) return;

    let correctAll = 0;
    let totalYin = 0;
    let correctYin = 0;
    let totalXing = 0;
    let correctXing = 0;

    questions.forEach((q) => {
      const userAns = (state.quiz.userAnswers[q.id] || '').trim();
      const isCorrect = userAns === q.answer;
      if (isCorrect) correctAll++;

      if (q.type === 'pronunciation') {
        totalYin++;
        if (isCorrect) correctYin++;
      } else {
        totalXing++;
        if (isCorrect) correctXing++;
      }
    });

    const wrongAll = total - correctAll;
    const score = Math.round((correctAll / total) * 100);

    const scoreEl = document.getElementById('quiz-res-score');
    scoreEl.textContent = String(score);
    scoreEl.className = `score-number ${score >= 80 ? 'high' : score >= 60 ? 'mid' : 'low'}`;

    document.getElementById('quiz-res-accuracy').textContent = `答對 ${correctAll} / ${total} 題（正確率 ${score}%）`;
    document.getElementById('quiz-res-yin').textContent = totalYin > 0 ? `${correctYin} / ${totalYin} 題` : '未測驗';
    document.getElementById('quiz-res-xing').textContent = totalXing > 0 ? `${correctXing} / ${totalXing} 題` : '未測驗';

    const mm = String(Math.floor(state.quiz.elapsedSeconds / 60)).padStart(2, '0');
    const ss = String(state.quiz.elapsedSeconds % 60).padStart(2, '0');
    document.getElementById('quiz-res-time').textContent = `${mm} 分 ${ss} 秒`;

    document.getElementById('btn-res-filter-all').textContent = `全部題目 (${total})`;
    document.getElementById('btn-res-filter-wrong').textContent = `✗ 僅看答錯與未答 (${wrongAll})`;

    renderQuizResultTable();
  }

  function renderQuizResultTable() {
    const tbody = document.getElementById('quiz-result-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    const onlyWrong = state.quiz.resultFilter === 'wrong';

    state.quiz.questions.forEach((q, idx) => {
      const userAns = (state.quiz.userAnswers[q.id] || '').trim();
      const isCorrect = userAns === q.answer;
      if (onlyWrong && isCorrect) return;

      const isStarred = Boolean(state.records.starredMap[q.id]);
      const typeBadgeHtml =
        q.type === 'pronunciation'
          ? '<span class="badge badge-type yin">字音</span>'
          : '<span class="badge badge-type xing">字形</span>';

      const userAnsHtml = userAns
        ? `<span class="quiz-user-ans ${isCorrect ? 'correct' : 'wrong'}">${escapeHtml(userAns)}</span>`
        : '<span class="quiz-user-ans empty">（未作答）</span>';

      const statusBadgeHtml = isCorrect
        ? '<span class="badge badge-status mastered">✓ 答對</span>'
        : '<span class="badge badge-status wrong">✗ 答錯</span>';

      const tr = document.createElement('tr');
      tr.className = isCorrect ? 'res-row-correct' : 'res-row-wrong';
      tr.innerHTML = `
        <td class="col-star" data-label="收藏">
          <button type="button" class="star-cell-btn ${isStarred ? 'starred' : ''}" data-quiz-star-id="${q.id}" title="加入或取消重點收藏">
            ${isStarred ? '★' : '☆'}
          </button>
        </td>
        <td class="col-num" data-label="題序"><strong>#${idx + 1}</strong></td>
        <td class="col-year" data-label="出處">${q.year}年 (${q.num_str})</td>
        <td class="col-type" data-label="題型">${typeBadgeHtml}</td>
        <td class="col-prompt" data-label="題目">${formatPromptHtml(q)}</td>
        <td class="col-target" data-label="目標">${escapeHtml(q.target)}</td>
        <td class="col-user-ans" data-label="您的作答">${userAnsHtml}</td>
        <td class="col-answer" data-label="標準答案"><strong class="res-std-ans">${escapeHtml(q.answer)}</strong></td>
        <td class="col-status" data-label="結果">${statusBadgeHtml}</td>
        <td class="col-action" data-label="原卷">
          <a href="${getPdfPathForYear(q.year)}" target="_blank" rel="noopener" class="btn-ghost btn-sm">📄 原卷</a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // =========================================================================
  // 6-C. 第三階段：3. 紙本試卷 Word (.docx) 產生器與即時預覽
  // =========================================================================
  function buildDocxYearChips() {
    const container = document.getElementById('docx-year-chips');
    if (!container) return;
    container.innerHTML = '';

    state.years.forEach((y) => {
      const yearNum = Number(y);
      const btn = document.createElement('button');
      btn.type = 'button';
      const isSelected = state.docx.selectedYears.has(yearNum);
      btn.className = `year-chip ${isSelected ? 'active' : ''}`;
      btn.dataset.year = String(yearNum);
      btn.setAttribute('aria-pressed', String(isSelected));
      btn.innerHTML = `<span class="year-chip-check">${isSelected ? '✓' : '+'}</span><span>${yearNum}年</span>`;
      btn.addEventListener('click', () => {
        if (state.docx.selectedYears.has(yearNum)) {
          state.docx.selectedYears.delete(yearNum);
        } else {
          state.docx.selectedYears.add(yearNum);
        }
        resampleDocxQuestions();
      });
      container.appendChild(btn);
    });
  }

  function splitQuestionPromptParts(q) {
    const prompt = String(q.prompt || '');
    const target = String(q.target || '');

    if (q.type === 'pronunciation') {
      const idx = prompt.indexOf(target);
      if (idx >= 0) {
        return {
          before: prompt.slice(0, idx),
          target: target,
          after: prompt.slice(idx + target.length)
        };
      }
    } else {
      const reg = new RegExp(`\\s*${escapeRegExp(target)}\\s*`);
      const match = reg.exec(prompt);
      if (match) {
        return {
          before: prompt.slice(0, match.index),
          target: target,
          after: prompt.slice(match.index + match[0].length)
        };
      }
    }
    return { before: prompt, target: '', after: '' };
  }

  function formatDocxPreviewPromptHtml(q) {
    const { before, target, after } = splitQuestionPromptParts(q);
    if (!target) return escapeHtml(before);
    const underlineClass = state.docx.bracketStyle === 'corner_underline' ? 'docx-target-ul' : '';
    return `${escapeHtml(before)}「<span class="docx-target-inner ${underlineClass}">${escapeHtml(target)}</span>」${escapeHtml(after)}`;
  }

  function getDocxCandidatePools() {
    const { selectedYears, qSource } = state.docx;
    const yearQuestions = state.allQuestions.filter((q) => selectedYears.has(Number(q.year)));

    let primaryYin = [];
    let primaryXing = [];
    let fallbackYin = [];
    let fallbackXing = [];

    yearQuestions.forEach((q) => {
      const qStatus = state.records.statusMap[q.id] || 'unpracticed';
      const isStarred = Boolean(state.records.starredMap[q.id]);

      if (qSource === 'weak') {
        if (qStatus === 'wrong' || isStarred) {
          if (q.type === 'pronunciation') primaryYin.push(q);
          else primaryXing.push(q);
        }
      } else if (qSource === 'unpracticed') {
        if (qStatus === 'unpracticed') {
          if (q.type === 'pronunciation') primaryYin.push(q);
          else primaryXing.push(q);
        } else {
          if (q.type === 'pronunciation') fallbackYin.push(q);
          else fallbackXing.push(q);
        }
      } else {
        if (q.type === 'pronunciation') primaryYin.push(q);
        else primaryXing.push(q);
      }
    });

    return { primaryYin, primaryXing, fallbackYin, fallbackXing };
  }

  function resampleDocxQuestions() {
    const { primaryYin, primaryXing, fallbackYin, fallbackXing } = getDocxCandidatePools();
    const { qType, qCount } = state.docx;

    const sampleFromPool = (prim, fall, needed) => {
      const sPrim = shuffleArray([...prim]);
      if (sPrim.length >= needed) {
        return sPrim.slice(0, needed);
      }
      const sFall = shuffleArray([...fall]);
      return [...sPrim, ...sFall.slice(0, needed - sPrim.length)];
    };

    const availYin = primaryYin.length + fallbackYin.length;
    const availXing = primaryXing.length + fallbackXing.length;

    let chosenYin = [];
    let chosenXing = [];

    if (qType === 'pronunciation') {
      chosenYin = sampleFromPool(primaryYin, fallbackYin, Math.min(qCount, availYin));
    } else if (qType === 'character') {
      chosenXing = sampleFromPool(primaryXing, fallbackXing, Math.min(qCount, availXing));
    } else {
      const half = Math.floor(qCount / 2);
      let dYin = Math.min(half, availYin);
      let dXing = Math.min(qCount - dYin, availXing);
      if (dYin + dXing < qCount) {
        const rem = qCount - (dYin + dXing);
        if (availYin > dYin) dYin += Math.min(rem, availYin - dYin);
        else if (availXing > dXing) dXing += Math.min(rem, availXing - dXing);
      }
      chosenYin = sampleFromPool(primaryYin, fallbackYin, dYin);
      chosenXing = sampleFromPool(primaryXing, fallbackXing, dXing);
    }

    state.docx.sampledQuestions = [...chosenYin, ...chosenXing];
    updateDocxUIAndPreview();
  }

  function getDocxYearsDescription() {
    const selectedSet = state.docx.selectedYears;
    const totalYears = state.years.length;
    const selectedArr = state.years.map(Number).filter((y) => selectedSet.has(y));
    if (selectedArr.length === totalYears) return '101～114 年全題庫';
    if (selectedArr.length === 0) return '未選擇年度';
    if (selectedArr.length <= 6) return `民國 ${selectedArr.join('、')} 年`;
    return `自選 ${selectedArr.length} 個年度組合`;
  }

  function updateDocxUIAndPreview() {
    const selectedSet = state.docx.selectedYears;
    const totalYears = state.years.length;
    const selectedArr = state.years.map(Number).filter((y) => selectedSet.has(y));
    const count = selectedArr.length;

    document.querySelectorAll('#docx-year-chips .year-chip').forEach((btn) => {
      const y = Number(btn.dataset.year);
      const isSelected = selectedSet.has(y);
      btn.classList.toggle('active', isSelected);
      btn.setAttribute('aria-pressed', String(isSelected));
      const checkSpan = btn.querySelector('.year-chip-check');
      if (checkSpan) checkSpan.textContent = isSelected ? '✓' : '+';
    });

    const summaryEl = document.getElementById('docx-year-summary');
    if (summaryEl) {
      const combinedTotal = count * 200;
      if (count === totalYears) {
        summaryEl.textContent = `全部 ${totalYears} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text';
      } else if (count === 0) {
        summaryEl.textContent = '尚未選擇年度（請點選下方年度）';
        summaryEl.className = 'year-summary-text empty';
      } else if (count <= 5) {
        summaryEl.textContent = `已選 ${selectedArr.join('、')} 年（${count} 個年度・共 ${combinedTotal.toLocaleString()} 題）`;
        summaryEl.className = 'year-summary-text active';
      } else {
        summaryEl.textContent = `已選 ${count} 個年度・共 ${combinedTotal.toLocaleString()} 題`;
        summaryEl.className = 'year-summary-text active';
      }
    }

    const sampled = state.docx.sampledQuestions;
    const yinCount = sampled.filter((q) => q.type === 'pronunciation').length;
    const xingCount = sampled.filter((q) => q.type === 'character').length;

    const orientLabel = state.docx.orientation === 'landscape' ? '橫向紙張' : '直向紙張';
    const textDirLabel = state.docx.textDir === 'vertical' ? '直向文字（傳統直書）' : '橫向文字（現代橫書）';
    const layoutDesc = `${state.docx.paperSize} ${orientLabel}・${textDirLabel}・「」括號標示`;

    const statusEl = document.getElementById('docx-pool-status');
    if (statusEl) {
      statusEl.innerHTML = `目前已抽出：<strong>${sampled.length}</strong> 題（字音 ${yinCount} 題、字形 ${xingCount} 題）｜版面：<strong>${layoutDesc}</strong>`;
    }

    const metaBadge = document.getElementById('docx-preview-meta-badge');
    if (metaBadge) {
      metaBadge.textContent = layoutDesc;
    }

    const hasQuestions = sampled.length > 0;
    document.getElementById('btn-docx-dl-student').disabled = !hasQuestions;
    document.getElementById('btn-docx-dl-teacher').disabled = !hasQuestions;
    document.getElementById('btn-docx-dl-both').disabled = !hasQuestions;

    renderDocxPaperPreview();
  }

  function renderDocxPaperPreview() {
    const sheetEl = document.getElementById('docx-paper-sheet');
    if (!sheetEl) return;

    const { paperSize, orientation, textDir, previewMode, sampledQuestions } = state.docx;
    const titleInput = document.getElementById('docx-title-input');
    const customTitle = (titleInput && titleInput.value.trim()) || state.docx.title;
    const isTeacher = previewMode === 'teacher';

    sheetEl.className = `docx-paper-sheet paper-${paperSize.toLowerCase()} orient-${orientation} text-${textDir}`;

    if (sampledQuestions.length === 0) {
      sheetEl.innerHTML = '<div style="padding:2rem;text-align:center;color:#87908b;">目前未抽出任何題目，請勾選上方年度或調整篩選條件。</div>';
      return;
    }

    const yinList = sampledQuestions.filter((q) => q.type === 'pronunciation');
    const xingList = sampledQuestions.filter((q) => q.type === 'character');

    const buildSectionPreviewHtml = (secTitle, list) => {
      if (list.length === 0) return '';

      if (textDir === 'vertical') {
        // 直向文字：分區段（每區段依紙張寬度排列，由右至左，每題上為題號、中為答案格、下為直排「」題目）
        const colsPerBand =
          paperSize === 'A4' && orientation === 'portrait'
            ? 15
            : orientation === 'landscape' && (paperSize === 'B4' || paperSize === 'A3')
            ? 25
            : 20;

        let bandsHtml = '';
        for (let start = 0; start < list.length; start += colsPerBand) {
          const slice = list.slice(start, start + colsPerBand);
          let colsHtml = '';
          for (let i = 0; i < colsPerBand; i++) {
            const q = slice[i];
            const seqStr = String(start + i + 1).padStart(3, '0');
            if (q) {
              const ansHtml = isTeacher ? `<span class="pv-ans-filled">${escapeHtml(q.answer)}</span>` : '';
              colsHtml += `
                <div class="pv-v-col">
                  <div class="pv-v-num">${seqStr}</div>
                  <div class="pv-v-ans">${ansHtml}</div>
                  <div class="pv-v-prompt">${formatDocxPreviewPromptHtml(q)}</div>
                </div>
              `;
            } else {
              colsHtml += `
                <div class="pv-v-col empty">
                  <div class="pv-v-num"></div>
                  <div class="pv-v-ans"></div>
                  <div class="pv-v-prompt"></div>
                </div>
              `;
            }
          }
          bandsHtml += `<div class="pv-v-band">${colsHtml}</div>`;
        }

        return `
          <div class="pv-section">
            <div class="pv-sec-title">${escapeHtml(secTitle)}（共 ${list.length} 題，將「 」內測驗字或注音之正確解答填入上方空格）</div>
            ${bandsHtml}
          </div>
        `;
      } else {
        // 橫向文字：多欄表格橫排
        const colsPerRow =
          paperSize === 'A4' && orientation === 'portrait'
            ? 2
            : orientation === 'landscape' && (paperSize === 'B4' || paperSize === 'A3')
            ? 4
            : 3;

        let rowsHtml = '';
        for (let r = 0; r < list.length; r += colsPerRow) {
          let cellsHtml = '';
          for (let c = 0; c < colsPerRow; c++) {
            const q = list[r + c];
            if (q) {
              const seqStr = String(r + c + 1).padStart(3, '0');
              const ansHtml = isTeacher ? `<span class="pv-ans-filled">${escapeHtml(q.answer)}</span>` : '';
              cellsHtml += `
                <td class="pv-h-num">${seqStr}</td>
                <td class="pv-h-ans">${ansHtml}</td>
                <td class="pv-h-prompt">${formatDocxPreviewPromptHtml(q)}</td>
              `;
            } else {
              cellsHtml += `<td class="pv-h-num"></td><td class="pv-h-ans"></td><td class="pv-h-prompt"></td>`;
            }
          }
          rowsHtml += `<tr>${cellsHtml}</tr>`;
        }

        return `
          <div class="pv-section">
            <div class="pv-sec-title">${escapeHtml(secTitle)}（共 ${list.length} 題，請將「 」內測驗目標之正確答案填入左側空格）</div>
            <table class="pv-h-table">
              <tbody>${rowsHtml}</tbody>
            </table>
          </div>
        `;
      }
    };

    const roleTag = isTeacher ? '【教師標準解答卷】' : '【學生測驗卷】';
    const metaSub = `範圍：${getDocxYearsDescription()}｜版面：${paperSize} ${orientation === 'landscape' ? '橫向' : '直向'}｜班級：_______ 座號：____ 姓名：__________ 得分：_______`;

    sheetEl.innerHTML = `
      <div class="pv-doc-header">
        <div class="pv-doc-title">${escapeHtml(customTitle)} ${roleTag}</div>
        <div class="pv-doc-meta">${escapeHtml(metaSub)}</div>
      </div>
      ${buildSectionPreviewHtml('甲、字音部分', yinList)}
      ${buildSectionPreviewHtml('乙、字形部分', xingList)}
    `;
  }

  // =========================================================================
  // 純前端零相依性 Word (.docx) OpenXML 與 ZIP 封裝核心
  // =========================================================================
  function escapeXml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  const CRC32_TABLE = (function () {
    const table = new Uint32Array(256);
    for (let i = 0; i < 256; i++) {
      let c = i;
      for (let k = 0; k < 8; k++) {
        c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      }
      table[i] = c >>> 0;
    }
    return table;
  })();

  function computeCrc32(bytes) {
    let crc = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) {
      crc = CRC32_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function createZipBlobFromEntries(entries) {
    const encoder = new TextEncoder();
    const fileRecords = entries.map((entry) => {
      const nameBytes = encoder.encode(entry.path);
      const dataBytes = typeof entry.content === 'string' ? encoder.encode(entry.content) : entry.content;
      const crc = computeCrc32(dataBytes);
      return { nameBytes, dataBytes, crc };
    });

    let localSize = 0;
    let centralSize = 0;
    fileRecords.forEach((rec) => {
      localSize += 30 + rec.nameBytes.length + rec.dataBytes.length;
      centralSize += 46 + rec.nameBytes.length;
    });

    const totalSize = localSize + centralSize + 22;
    const buf = new ArrayBuffer(totalSize);
    const view = new DataView(buf);
    const outBytes = new Uint8Array(buf);

    let offset = 0;
    fileRecords.forEach((rec) => {
      rec.localHeaderOffset = offset;
      view.setUint32(offset, 0x04034b50, true); // Local file header signature
      view.setUint16(offset + 4, 20, true); // Version needed to extract (2.0)
      view.setUint16(offset + 6, 0x0800, true); // General purpose bit flag (UTF-8)
      view.setUint16(offset + 8, 0, true); // Compression method: 0 (STORE)
      view.setUint16(offset + 10, 0, true); // Last mod file time
      view.setUint16(offset + 12, 0x21, true); // Last mod file date
      view.setUint32(offset + 14, rec.crc, true); // CRC-32
      view.setUint32(offset + 18, rec.dataBytes.length, true); // Compressed size
      view.setUint32(offset + 22, rec.dataBytes.length, true); // Uncompressed size
      view.setUint16(offset + 26, rec.nameBytes.length, true); // File name length
      view.setUint16(offset + 28, 0, true); // Extra field length
      offset += 30;

      outBytes.set(rec.nameBytes, offset);
      offset += rec.nameBytes.length;

      outBytes.set(rec.dataBytes, offset);
      offset += rec.dataBytes.length;
    });

    const centralDirStart = offset;
    fileRecords.forEach((rec) => {
      view.setUint32(offset, 0x02014b50, true); // Central directory file header signature
      view.setUint16(offset + 4, 20, true); // Version made by
      view.setUint16(offset + 6, 20, true); // Version needed to extract
      view.setUint16(offset + 8, 0x0800, true); // General purpose bit flag (UTF-8)
      view.setUint16(offset + 10, 0, true); // Compression method: 0 (STORE)
      view.setUint16(offset + 12, 0, true); // Last mod file time
      view.setUint16(offset + 14, 0x21, true); // Last mod file date
      view.setUint32(offset + 16, rec.crc, true); // CRC-32
      view.setUint32(offset + 20, rec.dataBytes.length, true); // Compressed size
      view.setUint32(offset + 24, rec.dataBytes.length, true); // Uncompressed size
      view.setUint16(offset + 28, rec.nameBytes.length, true); // File name length
      view.setUint16(offset + 30, 0, true); // Extra field length
      view.setUint16(offset + 32, 0, true); // File comment length
      view.setUint16(offset + 34, 0, true); // Disk number start
      view.setUint16(offset + 36, 0, true); // Internal file attributes
      view.setUint32(offset + 38, 0, true); // External file attributes
      view.setUint32(offset + 42, rec.localHeaderOffset, true); // Relative offset of local header
      offset += 46;

      outBytes.set(rec.nameBytes, offset);
      offset += rec.nameBytes.length;
    });

    const centralDirSize = offset - centralDirStart;
    view.setUint32(offset, 0x06054b50, true); // End of central directory signature
    view.setUint16(offset + 4, 0, true); // Number of this disk
    view.setUint16(offset + 6, 0, true); // Disk where central directory starts
    view.setUint16(offset + 8, fileRecords.length, true); // Number of central directory records on this disk
    view.setUint16(offset + 10, fileRecords.length, true); // Total number of central directory records
    view.setUint32(offset + 12, centralDirSize, true); // Size of central directory
    view.setUint32(offset + 16, centralDirStart, true); // Offset of start of central directory
    view.setUint16(offset + 20, 0, true); // Comment length

    return new Blob([buf], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    });
  }

  function buildOpenXmlPromptRuns(q, fontSizeHalfPt, bracketStyle) {
    const { before, target, after } = splitQuestionPromptParts(q);
    const rPrNormal = `<w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:sz w:val="${fontSizeHalfPt}"/><w:szCs w:val="${fontSizeHalfPt}"/></w:rPr>`;
    const rPrTarget =
      bracketStyle === 'corner_underline'
        ? `<w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:b/><w:u w:val="single"/><w:sz w:val="${fontSizeHalfPt}"/><w:szCs w:val="${fontSizeHalfPt}"/></w:rPr>`
        : `<w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:b/><w:sz w:val="${fontSizeHalfPt}"/><w:szCs w:val="${fontSizeHalfPt}"/></w:rPr>`;

    if (!target) {
      return `<w:r>${rPrNormal}<w:t>${escapeXml(before)}</w:t></w:r>`;
    }

    let xml = '';
    if (before) {
      xml += `<w:r>${rPrNormal}<w:t>${escapeXml(before)}</w:t></w:r>`;
    }
    xml += `<w:r>${rPrNormal}<w:t>「</w:t></w:r>`;
    xml += `<w:r>${rPrTarget}<w:t>${escapeXml(target)}</w:t></w:r>`;
    xml += `<w:r>${rPrNormal}<w:t>」</w:t></w:r>`;
    if (after) {
      xml += `<w:r>${rPrNormal}<w:t>${escapeXml(after)}</w:t></w:r>`;
    }
    return xml;
  }

  function buildRunPropsXml(fontSizeHalfPt, options) {
    const opts = options || {};
    const bold = opts.bold ? '<w:b/>' : '';
    const underline = opts.underline ? '<w:u w:val="single"/>' : '';
    const color = opts.color ? `<w:color w:val="${opts.color}"/>` : '';
    return `<w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/>${bold}${underline}${color}<w:sz w:val="${fontSizeHalfPt}"/><w:szCs w:val="${fontSizeHalfPt}"/></w:rPr>`;
  }

  // 直書不用 Word 的 textDirection。tbRl 會把所有字向右轉 90 度；tbRlV 雖然國字直立，注音仍會躺倒。
  // 改成一格內由上而下、每個字一段，字面保持直立，與網頁 vertical-rl + text-orientation: upright 相同。
  function buildUprightStackParagraphs(segments, fontSizeHalfPt) {
    const lineTwips = fontSizeHalfPt * 10;
    const pPr = `<w:pPr><w:jc w:val="center"/><w:snapToGrid w:val="0"/><w:spacing w:before="0" w:after="0" w:line="${lineTwips}" w:lineRule="exact"/><w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr>`;
    let xml = '';
    segments.forEach((seg) => {
      const rPr = buildRunPropsXml(fontSizeHalfPt, seg);
      Array.from(String(seg.text || '')).forEach((ch) => {
        xml += `<w:p>${pPr}<w:r>${rPr}<w:t xml:space="preserve">${escapeXml(ch)}</w:t></w:r></w:p>`;
      });
    });
    if (!xml) {
      xml = `<w:p>${pPr}<w:r><w:t></w:t></w:r></w:p>`;
    }
    return xml;
  }

  function buildUprightPromptParagraphs(q, fontSizeHalfPt, bracketStyle) {
    const { before, target, after } = splitQuestionPromptParts(q);
    if (!target) {
      return buildUprightStackParagraphs([{ text: before }], fontSizeHalfPt);
    }
    const targetOpts = { text: target, bold: true, underline: bracketStyle === 'corner_underline' };
    // 網頁直排（vertical-rl）會把「」顯示成直排字形 ﹁﹂，橫筆與國字同寬。
    // Word 直書是逐字直立，若仍放橫排「」，標楷體筆畫只剩約三分之一寬。
    return buildUprightStackParagraphs(
      [
        { text: before },
        { text: '﹁' },
        targetOpts,
        { text: '﹂' },
        { text: after }
      ],
      fontSizeHalfPt
    );
  }

  function buildDocxSheetBodyXml(questions, isTeacherCopy, includePageBreakBefore) {
    const { paperSize, orientation, textDir, bracketStyle } = state.docx;
    const titleInput = document.getElementById('docx-title-input');
    const customTitle = (titleInput && titleInput.value.trim()) || state.docx.title;

    // 紙張尺寸（twips：1mm = 56.6929 twips）
    const paperDims = {
      A4: { short: 11906, long: 16838 }, // 210 x 297 mm
      B4: { short: 14570, long: 20636 }, // 257 x 364 mm (JIS B4)
      A3: { short: 16838, long: 23811 }  // 297 x 420 mm
    };
    const dim = paperDims[paperSize] || paperDims.A4;
    const pageW = orientation === 'landscape' ? dim.long : dim.short;
    const marginLR = 720; // 左右邊界各 0.5 吋 (720 twips)
    const contentW = pageW - marginLR * 2;

    const yinList = questions.filter((q) => q.type === 'pronunciation');
    const xingList = questions.filter((q) => q.type === 'character');

    const roleTag = isTeacherCopy ? '【教師標準解答卷】' : '【學生作答卷】';
    const metaSub = `範圍：${getDocxYearsDescription()}　｜　版面：${paperSize} ${orientation === 'landscape' ? '橫向' : '直向'}　｜　班級：_________　座號：______　姓名：_____________　得分：_________`;

    let xml = '';
    if (includePageBreakBefore) {
      xml += `<w:p><w:r><w:br w:type="page"/></w:r></w:p>`;
    }

    // 試卷主標題與學生資料列
    xml += `
      <w:p>
        <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="80"/></w:pPr>
        <w:r>
          <w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>
          <w:t>${escapeXml(customTitle)} ${escapeXml(roleTag)}</w:t>
        </w:r>
      </w:p>
      <w:p>
        <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="140"/></w:pPr>
        <w:r>
          <w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>
          <w:t>${escapeXml(metaSub)}</w:t>
        </w:r>
      </w:p>
    `;

    const buildSectionXml = (secTitle, list) => {
      if (list.length === 0) return '';

      let secXml = `
        <w:p>
          <w:pPr><w:spacing w:before="100" w:after="60"/></w:pPr>
          <w:r>
            <w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
            <w:t>${escapeXml(secTitle)}（共 ${list.length} 題，請將「 」內測驗字或注音之正確答案填入空格內）：</w:t>
          </w:r>
        </w:p>
      `;

      const tblBorders = `
        <w:tblBorders>
          <w:top w:val="single" w:sz="6" w:space="0" w:color="333333"/>
          <w:left w:val="single" w:sz="6" w:space="0" w:color="333333"/>
          <w:bottom w:val="single" w:sz="6" w:space="0" w:color="333333"/>
          <w:right w:val="single" w:sz="6" w:space="0" w:color="333333"/>
          <w:insideH w:val="single" w:sz="4" w:space="0" w:color="555555"/>
          <w:insideV w:val="single" w:sz="4" w:space="0" w:color="555555"/>
        </w:tblBorders>
      `;

      if (textDir === 'vertical') {
        // 直向文字：傳統競賽試卷直排區段表格（由右至左題序，每欄含：題號列、直書作答格、直書「」題目列）
        const colsPerBand =
          paperSize === 'A4' && orientation === 'portrait'
            ? 15
            : orientation === 'landscape' && (paperSize === 'B4' || paperSize === 'A3')
            ? 25
            : 20;

        const colW = Math.floor(contentW / colsPerBand);
        const fontPtHalf = colsPerBand >= 25 && paperSize === 'A4' ? 22 : 24;
        const lineTwips = fontPtHalf * 10;
        const textLen = (s) => Array.from(String(s || '')).length;

        for (let start = 0; start < list.length; start += colsPerBand) {
          const slice = list.slice(start, start + colsPerBand);
          let maxAnsChars = 1;
          let maxPromptChars = 1;
          slice.forEach((q) => {
            if (!q) return;
            if (isTeacherCopy) maxAnsChars = Math.max(maxAnsChars, textLen(q.answer));
            const parts = splitQuestionPromptParts(q);
            const promptLen = textLen(parts.before) + textLen(parts.target) + textLen(parts.after) + (parts.target ? 2 : 0);
            maxPromptChars = Math.max(maxPromptChars, Math.max(promptLen, 1));
          });
          // 解答與題目都排成同一直行。列高一次放進整段，避免折成旁邊第二行。
          const ansRowH = Math.max(4, maxAnsChars) * lineTwips + 120;
          const promptRowH = Math.max(4, maxPromptChars) * lineTwips + 160;

          let gridColsXml = '';
          for (let c = 0; c < colsPerBand; c++) {
            gridColsXml += `<w:gridCol w:w="${colW}"/>`;
          }

          let rowNumCells = '';
          let rowAnsCells = '';
          let rowPromptCells = '';

          // 由左至右建立儲存格時，最右側欄（colIdx = colsPerBand - 1）對應本區段第 1 題（由右至左閱讀）
          for (let colIdx = 0; colIdx < colsPerBand; colIdx++) {
            const qOffset = colsPerBand - 1 - colIdx;
            const q = slice[qOffset];
            const seqNum = start + qOffset + 1;
            const seqStr = q ? String(seqNum).padStart(3, '0') : '';

            // 第 1 列：題號
            rowNumCells += `
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${colW}" w:type="dxa"/>
                  <w:vAlign w:val="center"/>
                  <w:shd w:val="clear" w:color="auto" w:fill="F4F4F0"/>
                </w:tcPr>
                <w:p>
                  <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0"/></w:pPr>
                  <w:r>
                    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="標楷體"/><w:b/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
                    <w:t>${escapeXml(seqStr)}</w:t>
                  </w:r>
                </w:p>
              </w:tc>
            `;

            // 第 2 列：答案方格。整段解答留在同一格，由上而下排成同一直行。
            const ansText = q && isTeacherCopy ? q.answer : '';
            const ansParas = buildUprightStackParagraphs(
              [{ text: ansText, bold: true, color: '1B4D3E' }],
              fontPtHalf
            );
            rowAnsCells += `
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${colW}" w:type="dxa"/>
                  <w:vAlign w:val="center"/>
                </w:tcPr>
                ${ansParas}
              </w:tc>
            `;

            // 第 3 列：直向題目。字直立由上而下，注音也不躺倒。
            const promptParas = q
              ? buildUprightPromptParagraphs(q, fontPtHalf, bracketStyle)
              : buildUprightStackParagraphs([{ text: '' }], fontPtHalf);
            rowPromptCells += `
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${colW}" w:type="dxa"/>
                  <w:vAlign w:val="top"/>
                </w:tcPr>
                ${promptParas}
              </w:tc>
            `;
          }

          secXml += `
            <w:tbl>
              <w:tblPr>
                <w:tblW w:w="${contentW}" w:type="dxa"/>
                <w:jc w:val="center"/>
                ${tblBorders}
                <w:tblCellMar>
                  <w:top w:w="40" w:type="dxa"/>
                  <w:left w:w="20" w:type="dxa"/>
                  <w:bottom w:w="40" w:type="dxa"/>
                  <w:right w:w="20" w:type="dxa"/>
                </w:tblCellMar>
              </w:tblPr>
              <w:tblGrid>${gridColsXml}</w:tblGrid>
              <w:tr>
                <w:trPr><w:trHeight w:val="320" w:hRule="atLeast"/></w:trPr>
                ${rowNumCells}
              </w:tr>
              <w:tr>
                <w:trPr><w:trHeight w:val="${ansRowH}" w:hRule="atLeast"/></w:trPr>
                ${rowAnsCells}
              </w:tr>
              <w:tr>
                <w:trPr><w:trHeight w:val="${promptRowH}" w:hRule="atLeast"/></w:trPr>
                ${rowPromptCells}
              </w:tr>
            </w:tbl>
            <w:p><w:pPr><w:spacing w:before="0" w:after="80"/></w:pPr></w:p>
          `;
        }
      } else {
        // 橫向文字：多欄橫書表格（每題佔 3 格：題號 | 作答格 | 題目詞語）
        const groupsPerRow =
          paperSize === 'A4' && orientation === 'portrait'
            ? 2
            : orientation === 'landscape' && (paperSize === 'B4' || paperSize === 'A3')
            ? 4
            : 3;

        const groupW = Math.floor(contentW / groupsPerRow);
        const wNum = Math.floor(groupW * 0.13);
        const wAns = Math.floor(groupW * 0.30);
        const wPrompt = groupW - wNum - wAns;

        let gridColsXml = '';
        for (let g = 0; g < groupsPerRow; g++) {
          gridColsXml += `<w:gridCol w:w="${wNum}"/><w:gridCol w:w="${wAns}"/><w:gridCol w:w="${wPrompt}"/>`;
        }

        let rowsXml = '';
        for (let r = 0; r < list.length; r += groupsPerRow) {
          let rowCellsXml = '';
          for (let g = 0; g < groupsPerRow; g++) {
            const q = list[r + g];
            const seqStr = q ? String(r + g + 1).padStart(3, '0') : '';
            const ansText = q && isTeacherCopy ? q.answer : '';
            const promptRuns = q ? buildOpenXmlPromptRuns(q, 24, bracketStyle) : '<w:r><w:t></w:t></w:r>';

            rowCellsXml += `
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${wNum}" w:type="dxa"/>
                  <w:vAlign w:val="center"/>
                  <w:shd w:val="clear" w:color="auto" w:fill="F4F4F0"/>
                </w:tcPr>
                <w:p>
                  <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0"/></w:pPr>
                  <w:r>
                    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="標楷體"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>
                    <w:t>${escapeXml(seqStr)}</w:t>
                  </w:r>
                </w:p>
              </w:tc>
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${wAns}" w:type="dxa"/>
                  <w:noWrap/>
                  <w:vAlign w:val="center"/>
                </w:tcPr>
                <w:p>
                  <w:pPr>
                    <w:jc w:val="center"/>
                    <w:snapToGrid w:val="0"/>
                    <w:wordWrap w:val="off"/>
                    <w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>
                  </w:pPr>
                  <w:r>
                    <w:rPr><w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體"/><w:b/><w:color w:val="1B4D3E"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
                    <w:t>${escapeXml(ansText)}</w:t>
                  </w:r>
                </w:p>
              </w:tc>
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="${wPrompt}" w:type="dxa"/>
                  <w:vAlign w:val="center"/>
                </w:tcPr>
                <w:p>
                  <w:pPr><w:jc w:val="left"/><w:spacing w:before="0" w:after="0"/></w:pPr>
                  ${promptRuns}
                </w:p>
              </w:tc>
            `;
          }

          rowsXml += `
            <w:tr>
              <w:trPr><w:trHeight w:val="520" w:hRule="atLeast"/></w:trPr>
              ${rowCellsXml}
            </w:tr>
          `;
        }

        secXml += `
          <w:tbl>
            <w:tblPr>
              <w:tblW w:w="${contentW}" w:type="dxa"/>
              <w:jc w:val="center"/>
              ${tblBorders}
              <w:tblCellMar>
                <w:top w:w="50" w:type="dxa"/>
                <w:left w:w="80" w:type="dxa"/>
                <w:bottom w:w="50" w:type="dxa"/>
                <w:right w:w="80" w:type="dxa"/>
              </w:tblCellMar>
            </w:tblPr>
            <w:tblGrid>${gridColsXml}</w:tblGrid>
            ${rowsXml}
          </w:tbl>
          <w:p><w:pPr><w:spacing w:before="0" w:after="100"/></w:pPr></w:p>
        `;
      }

      return secXml;
    };

    xml += buildSectionXml('甲、字音部分', yinList);
    xml += buildSectionXml('乙、字形部分', xingList);
    return xml;
  }

  function generateAndDownloadDocx(exportMode) {
    const questions = state.docx.sampledQuestions;
    if (!questions || questions.length === 0) {
      alert('目前沒有可匯出的題目，請先選擇年度範圍並抽題。');
      return;
    }

    const { paperSize, orientation, textDir } = state.docx;
    const paperDims = {
      A4: { short: 11906, long: 16838 },
      B4: { short: 14570, long: 20636 },
      A3: { short: 16838, long: 23811 }
    };
    const dim = paperDims[paperSize] || paperDims.A4;
    const pageW = orientation === 'landscape' ? dim.long : dim.short;
    const pageH = orientation === 'landscape' ? dim.short : dim.long;
    const orientAttr = orientation === 'landscape' ? 'w:orient="landscape"' : 'w:orient="portrait"';

    let bodyContentXml = '';
    if (exportMode === 'student') {
      bodyContentXml = buildDocxSheetBodyXml(questions, false, false);
    } else if (exportMode === 'teacher') {
      bodyContentXml = buildDocxSheetBodyXml(questions, true, false);
    } else {
      bodyContentXml =
        buildDocxSheetBodyXml(questions, false, false) +
        buildDocxSheetBodyXml(questions, true, true);
    }

    const sectPrXml = `
      <w:sectPr>
        <w:pgSz w:w="${pageW}" w:h="${pageH}" ${orientAttr}/>
        <w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="360" w:footer="360" w:gutter="0"/>
        <w:docGrid w:linePitch="360"/>
      </w:sectPr>
    `;

    const documentXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    ${bodyContentXml}
    ${sectPrXml}
  </w:body>
</w:document>`;

    const contentTypesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>`;

    const rootRelsXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`;

    const docRelsXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
</Relationships>`;

    const stylesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="標楷體" w:hAnsi="標楷體" w:eastAsia="標楷體" w:cs="Times New Roman"/>
        <w:sz w:val="24"/>
        <w:szCs w:val="24"/>
        <w:lang w:val="en-US" w:eastAsia="zh-TW" w:bidi="ar-SA"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:after="0" w:line="240" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
</w:styles>`;

    const settingsXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:compat>
    <w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>
  </w:compat>
</w:settings>`;

    const blob = createZipBlobFromEntries([
      { path: '[Content_Types].xml', content: contentTypesXml },
      { path: '_rels/.rels', content: rootRelsXml },
      { path: 'word/_rels/document.xml.rels', content: docRelsXml },
      { path: 'word/styles.xml', content: stylesXml },
      { path: 'word/settings.xml', content: settingsXml },
      { path: 'word/document.xml', content: documentXml }
    ]);

    const orientStr = orientation === 'landscape' ? '橫向紙' : '直向紙';
    const dirStr = textDir === 'vertical' ? '直書' : '橫書';
    const modeStr =
      exportMode === 'student'
        ? '學生空白卷'
        : exportMode === 'teacher'
        ? '教師解答卷'
        : '題目與解答合訂卷';

    const fileName = `國語字音字形_${paperSize}_${orientStr}_${dirStr}_${questions.length}題_${modeStr}.docx`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 300);
  }

  // =========================================================================
  // 7. 事件綁定
  // =========================================================================
  function bindEvents() {
    // 頂部主功能導覽切換
    document.querySelectorAll('.main-nav .nav-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const mod = tab.dataset.module;
        state.activeModule = mod;
        document.querySelectorAll('.main-nav .nav-tab').forEach((t) => t.classList.toggle('active', t === tab));

        const filterPanel = document.querySelector('.filter-panel');
        const emptyState = document.getElementById('empty-state');
        const cardSection = document.getElementById('view-card');
        const listSection = document.getElementById('view-list');
        const quizSection = document.getElementById('module-quiz');
        const docxSection = document.getElementById('module-docx');
        const placeholder = document.getElementById('module-placeholder');

        if (mod === 'review') {
          filterPanel.classList.remove('hidden');
          quizSection.classList.add('hidden');
          docxSection.classList.add('hidden');
          placeholder.classList.add('hidden');
          applyFilters();
        } else if (mod === 'quiz') {
          filterPanel.classList.add('hidden');
          emptyState.classList.add('hidden');
          cardSection.classList.add('hidden');
          listSection.classList.add('hidden');
          docxSection.classList.add('hidden');
          placeholder.classList.add('hidden');
          quizSection.classList.remove('hidden');
          renderQuizStage();
        } else if (mod === 'docx') {
          filterPanel.classList.add('hidden');
          emptyState.classList.add('hidden');
          cardSection.classList.add('hidden');
          listSection.classList.add('hidden');
          quizSection.classList.add('hidden');
          placeholder.classList.add('hidden');
          docxSection.classList.remove('hidden');
          if (state.docx.sampledQuestions.length === 0) {
            resampleDocxQuestions();
          } else {
            updateDocxUIAndPreview();
          }
        }
      });
    });

    document.getElementById('btn-back-to-review').addEventListener('click', () => {
      document.querySelector('.main-nav .nav-tab[data-module="review"]').click();
    });

    // 年度複選快速按鈕（全選、近 5 年、近 3 年、清空重選）
    const setSelectedYearsAndApply = (yearList) => {
      state.filters.selectedYears = new Set(yearList.map(Number));
      updateYearChipsUI();
      applyFilters();
    };

    const btnYearAll = document.getElementById('btn-year-all');
    if (btnYearAll) {
      btnYearAll.addEventListener('click', () => setSelectedYearsAndApply(state.years));
    }
    const btnYearRecent5 = document.getElementById('btn-year-recent5');
    if (btnYearRecent5) {
      btnYearRecent5.addEventListener('click', () => setSelectedYearsAndApply(state.years.slice(-5)));
    }
    const btnYearRecent3 = document.getElementById('btn-year-recent3');
    if (btnYearRecent3) {
      btnYearRecent3.addEventListener('click', () => setSelectedYearsAndApply(state.years.slice(-3)));
    }
    const btnYearClear = document.getElementById('btn-year-clear');
    if (btnYearClear) {
      btnYearClear.addEventListener('click', () => setSelectedYearsAndApply([]));
    }

    // 題型篩選
    document.querySelectorAll('#filter-type-group .seg-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#filter-type-group .seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
        state.filters.type = btn.dataset.type;
        applyFilters();
      });
    });

    // 複習狀態篩選
    document.getElementById('filter-status').addEventListener('change', (e) => {
      state.filters.status = e.target.value;
      applyFilters();
    });

    // 關鍵字搜尋
    const kwInput = document.getElementById('filter-keyword');
    const clearSearchBtn = document.getElementById('btn-clear-search');
    kwInput.addEventListener('input', () => {
      state.filters.keyword = kwInput.value;
      clearSearchBtn.classList.toggle('hidden', !kwInput.value);
      applyFilters();
    });
    clearSearchBtn.addEventListener('click', () => {
      kwInput.value = '';
      state.filters.keyword = '';
      clearSearchBtn.classList.add('hidden');
      applyFilters();
    });

    // 重設篩選
    document.getElementById('btn-reset-filters').addEventListener('click', () => {
      state.filters = {
        selectedYears: new Set(state.years.map(Number)),
        type: 'all',
        status: 'all',
        keyword: ''
      };
      updateYearChipsUI();
      document.getElementById('filter-status').value = 'all';
      kwInput.value = '';
      clearSearchBtn.classList.add('hidden');
      document.querySelectorAll('#filter-type-group .seg-btn').forEach((b) => {
        b.classList.toggle('active', b.dataset.type === 'all');
      });
      applyFilters();
    });

    // 重置本機學習紀錄
    document.getElementById('btn-reset-progress').addEventListener('click', () => {
      if (confirm('確定要清除所有「已熟練」、「需加強（錯題）」與「★ 重點收藏」紀錄嗎？')) {
        state.records.statusMap = {};
        state.records.starredMap = {};
        saveLocalStorage();
        applyFilters();
      }
    });

    // 檢視模式切換（卡片 vs 列表）
    document.querySelectorAll('.view-mode-tabs .mode-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-mode-tabs .mode-btn').forEach((b) => b.classList.toggle('active', b === btn));
        state.viewMode = btn.dataset.view;
        renderCurrentView();
      });
    });

    // 答對自動下一題
    const chkAutoNext = document.getElementById('chk-auto-next');
    chkAutoNext.checked = state.autoNextOnCorrect;
    chkAutoNext.addEventListener('change', () => {
      state.autoNextOnCorrect = chkAutoNext.checked;
      saveLocalStorage();
    });

    // 隨機洗牌順序切換
    const shuffleBtn = document.getElementById('btn-toggle-shuffle');
    shuffleBtn.addEventListener('click', () => {
      state.isShuffled = !state.isShuffled;
      shuffleBtn.textContent = state.isShuffled ? '🔀 隨機洗牌順序：開（點此恢復）' : '🔀 隨機洗牌順序：關';
      shuffleBtn.classList.toggle('btn-Secondary-active', state.isShuffled);
      applyFilters();
    });

    // 手機版頂端標頭收合。預設收合，讓題目佔滿畫面；選擇會記在這台裝置。
    const headerEl = document.getElementById('site-header');
    const headerToggleBtn = document.getElementById('btn-toggle-header');
    const headerCollapsedKey = 'suHeaderCollapsed';
    const applyHeaderCollapsed = (collapsed) => {
      if (!headerEl || !headerToggleBtn) return;
      headerEl.classList.toggle('header-collapsed', collapsed);
      headerToggleBtn.setAttribute('aria-expanded', String(!collapsed));
      headerToggleBtn.textContent = collapsed ? '國立竹山高中　展開標頭 ▾' : '收合標頭 ▴';
    };
    if (headerEl && headerToggleBtn) {
      const savedHeader = localStorage.getItem(headerCollapsedKey);
      const collapsedOnPhone = window.innerWidth <= 768 && savedHeader !== '0';
      applyHeaderCollapsed(collapsedOnPhone);
      headerToggleBtn.addEventListener('click', () => {
        const nextCollapsed = !headerEl.classList.contains('header-collapsed');
        applyHeaderCollapsed(nextCollapsed);
        localStorage.setItem(headerCollapsedKey, nextCollapsed ? '1' : '0');
      });
    }

    // 手機版篩選面板展開/收合
    const mobileFilterBtn = document.getElementById('btn-toggle-mobile-filters');
    const filterControlsPanel = document.getElementById('filter-controls-panel');
    if (mobileFilterBtn && filterControlsPanel) {
      mobileFilterBtn.addEventListener('click', () => {
        const isCollapsed = filterControlsPanel.classList.toggle('mobile-collapsed');
        mobileFilterBtn.setAttribute('aria-expanded', String(!isCollapsed));
        mobileFilterBtn.textContent = isCollapsed ? '⚙️ 展開篩選與搜尋 ▾' : '⚙️ 收合篩選與搜尋 ▴';
      });
    }

    // 卡片導覽（上一題、下一題、跳題）
    document.getElementById('btn-prev-q').addEventListener('click', goPrevQuestion);
    document.getElementById('btn-next-q').addEventListener('click', goNextQuestion);
    document.getElementById('select-jump-q').addEventListener('change', (e) => {
      state.currentIndex = Number(e.target.value) || 0;
      renderQuestionCard();
      scrollBelowHeader(document.getElementById('q-prompt-area'));
    });

    // 手機觸控左右滑動題目區切換上下題
    const promptAreaEl = document.querySelector('.q-prompt-area');
    if (promptAreaEl) {
      let touchStartX = 0;
      let touchStartY = 0;
      promptAreaEl.addEventListener(
        'touchstart',
        (e) => {
          if (e.touches.length === 1) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
          }
        },
        { passive: true }
      );
      promptAreaEl.addEventListener(
        'touchend',
        (e) => {
          if (e.changedTouches.length === 1) {
            const dx = e.changedTouches[0].clientX - touchStartX;
            const dy = e.changedTouches[0].clientY - touchStartY;
            if (Math.abs(dx) > 55 && Math.abs(dy) < 40) {
              if (dx < 0) {
                goNextQuestion();
              } else {
                goPrevQuestion();
              }
            }
          }
        },
        { passive: true }
      );
    }

    // 卡片收藏重點按鈕
    document.getElementById('btn-star-q').addEventListener('click', () => {
      const q = state.filteredQuestions[state.currentIndex];
      if (q) toggleStarQuestion(q.id);
    });

    // 注音操作按鈕
    document.getElementById('btn-zhuyin-backspace').addEventListener('click', backspaceZhuyinSlot);
    document.getElementById('btn-zhuyin-clear').addEventListener('click', clearZhuyinSlots);
    document.getElementById('btn-check-pronunciation').addEventListener('click', checkPronunciationAnswer);
    document.getElementById('btn-reveal-pronunciation').addEventListener('click', revealCurrentAnswer);

    // 字形國字輸入操作按鈕與 IME 防誤觸 Enter
    const charInput = document.getElementById('char-answer-input');
    charInput.addEventListener('compositionstart', () => {
      isImeComposing = true;
    });
    charInput.addEventListener('compositionend', () => {
      isImeComposing = false;
    });
    charInput.addEventListener('keydown', (e) => {
      if (isImeComposing) return;
      if (e.key === 'Enter') {
        e.preventDefault();
        checkCharacterAnswer();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        charInput.value = '';
      } else if ((e.key === ' ' || e.key === 'F1') && charInput.value.trim() === '') {
        e.preventDefault();
        revealCurrentAnswer();
      } else if (e.key === 'ArrowLeft' && charInput.value === '') {
        e.preventDefault();
        goPrevQuestion();
      } else if (e.key === 'ArrowRight' && charInput.value === '') {
        e.preventDefault();
        goNextQuestion();
      }
    });

    document.getElementById('btn-char-clear').addEventListener('click', () => {
      charInput.value = '';
      charInput.focus();
    });
    document.getElementById('btn-check-character').addEventListener('click', checkCharacterAnswer);
    document.getElementById('btn-reveal-character').addEventListener('click', revealCurrentAnswer);

    // 答題回饋面板按鈕
    document.getElementById('btn-mark-mastered').addEventListener('click', () => {
      const q = state.filteredQuestions[state.currentIndex];
      if (q) setQuestionStatus(q.id, 'mastered');
    });
    document.getElementById('btn-mark-wrong').addEventListener('click', () => {
      const q = state.filteredQuestions[state.currentIndex];
      if (q) setQuestionStatus(q.id, 'wrong');
    });
    document.getElementById('btn-feedback-next').addEventListener('click', goNextQuestion);

    // 全域鍵盤快捷鍵（支援 1. 線上複習 與 2. 線上測驗）
    document.addEventListener('keydown', (e) => {
      if (isImeComposing) return;

      const activeEl = document.activeElement;
      const activeTag = activeEl ? activeEl.tagName.toLowerCase() : '';
      const isInputFocused = activeTag === 'input' || activeTag === 'select' || activeTag === 'textarea';

      // 線上測驗進行中之快捷鍵
      if (state.activeModule === 'quiz' && state.quiz.stage === 'running') {
        const q = state.quiz.questions[state.quiz.currentIndex];
        if (!q) return;

        if (e.key === 'ArrowLeft' && !isInputFocused) {
          e.preventDefault();
          if (state.quiz.currentIndex > 0) {
            state.quiz.currentIndex--;
            renderQuizRunner();
          }
        } else if (e.key === 'ArrowRight' && !isInputFocused) {
          e.preventDefault();
          if (state.quiz.currentIndex < state.quiz.questions.length - 1) {
            state.quiz.currentIndex++;
            renderQuizRunner();
          }
        } else if (!isInputFocused && q.type === 'pronunciation') {
          if (e.key === 'Backspace') {
            e.preventDefault();
            backspaceQuizZhuyinSlot();
          } else if (e.key === 'Escape') {
            e.preventDefault();
            clearQuizCurrentQuestionInput();
          } else if (e.key === 'Enter') {
            e.preventDefault();
            advanceOrSubmitQuizQuestion();
          }
        }
        return;
      }

      if (state.activeModule !== 'review' || state.viewMode !== 'card') return;

      const q = state.filteredQuestions[state.currentIndex];
      if (!q) return;

      // F2 隨時切換重點收藏，F1 隨時看答案
      if (e.key === 'F2') {
        e.preventDefault();
        toggleStarQuestion(q.id);
        return;
      }
      if (e.key === 'F1') {
        e.preventDefault();
        revealCurrentAnswer();
        return;
      }

      // 回饋面板顯示時，支援按 1 (標為已熟練)、按 2 (加入需加強)
      const feedbackVisible = !document.getElementById('feedback-panel').classList.contains('hidden');
      if (feedbackVisible && (!isInputFocused || (activeEl === charInput && charInput.value === ''))) {
        if (e.key === '1') {
          e.preventDefault();
          setQuestionStatus(q.id, 'mastered');
          return;
        } else if (e.key === '2') {
          e.preventDefault();
          setQuestionStatus(q.id, 'wrong');
          return;
        }
      }

      if (e.key === 'ArrowLeft' && !isInputFocused) {
        e.preventDefault();
        goPrevQuestion();
      } else if (e.key === 'ArrowRight' && !isInputFocused) {
        e.preventDefault();
        goNextQuestion();
      } else if (!isInputFocused && q.type === 'pronunciation') {
        if (e.key === 'Backspace') {
          e.preventDefault();
          backspaceZhuyinSlot();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          clearZhuyinSlots();
        } else if (e.key === 'Enter') {
          e.preventDefault();
          checkPronunciationAnswer();
        } else if (e.key === ' ') {
          e.preventDefault();
          revealCurrentAnswer();
        }
      }
    });

    // 列表模式控制項
    document.getElementById('btn-toggle-all-answers').addEventListener('click', () => {
      state.listMaskAll = !state.listMaskAll;
      state.listRevealedIds.clear();
      renderQuestionsList();
    });

    document.getElementById('select-page-size').addEventListener('change', (e) => {
      state.listPageSize = Number(e.target.value) || 100;
      state.listPage = 1;
      renderQuestionsList();
    });

    const changePage = (delta) => {
      state.listPage += delta;
      renderQuestionsList();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    document.getElementById('btn-page-prev').addEventListener('click', () => changePage(-1));
    document.getElementById('btn-page-next').addEventListener('click', () => changePage(1));
    document.getElementById('btn-page-prev-bottom').addEventListener('click', () => changePage(-1));
    document.getElementById('btn-page-next-bottom').addEventListener('click', () => changePage(1));

    // 列表表格事件委派（點擊收藏、遮罩翻開、練習此題）
    document.getElementById('questions-table-body').addEventListener('click', (e) => {
      const starBtn = e.target.closest('[data-star-id]');
      if (starBtn) {
        toggleStarQuestion(starBtn.dataset.starId);
        return;
      }

      const ansCell = e.target.closest('[data-ans-id]');
      if (ansCell) {
        const id = ansCell.dataset.ansId;
        if (state.listRevealedIds.has(id)) {
          state.listRevealedIds.delete(id);
        } else {
          state.listRevealedIds.add(id);
        }
        ansCell.classList.toggle('masked', state.listMaskAll && !state.listRevealedIds.has(id));
        return;
      }

      const practiceBtn = e.target.closest('[data-practice-idx]');
      if (practiceBtn) {
        state.currentIndex = Number(practiceBtn.dataset.practiceIdx) || 0;
        document.getElementById('btn-mode-card').click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });

    // =======================================================================
    // 線上測驗事件綁定
    // =======================================================================
    const setQuizYears = (yearList) => {
      state.quiz.selectedYears = new Set(yearList.map(Number));
      updateQuizSetupUI();
    };
    document.getElementById('btn-quiz-year-all').addEventListener('click', () => setQuizYears(state.years));
    document.getElementById('btn-quiz-year-recent5').addEventListener('click', () => setQuizYears(state.years.slice(-5)));
    document.getElementById('btn-quiz-year-recent3').addEventListener('click', () => setQuizYears(state.years.slice(-3)));
    document.getElementById('btn-quiz-year-clear').addEventListener('click', () => setQuizYears([]));

    const bindQuizOptionPills = (containerId, dataKey, stateProp, transformFn = (v) => v) => {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.querySelectorAll('.quiz-pill').forEach((btn) => {
        btn.addEventListener('click', () => {
          container.querySelectorAll('.quiz-pill').forEach((b) => b.classList.toggle('active', b === btn));
          state.quiz[stateProp] = transformFn(btn.dataset[dataKey]);
          updateQuizSetupUI();
        });
      });
    };

    bindQuizOptionPills('quiz-opt-type', 'qtype', 'qType');
    bindQuizOptionPills('quiz-opt-source', 'qsource', 'qSource');
    bindQuizOptionPills('quiz-opt-count', 'qcount', 'qCount', Number);
    bindQuizOptionPills('quiz-opt-timer', 'qtimer', 'timerMode');

    document.getElementById('btn-start-quiz').addEventListener('click', startQuiz);

    // 測驗進行中控制項
    document.getElementById('btn-quiz-toggle-palette').addEventListener('click', () => {
      state.quiz.paletteOpen = !state.quiz.paletteOpen;
      document.getElementById('quiz-palette-panel').classList.toggle('hidden', !state.quiz.paletteOpen);
      document.getElementById('btn-quiz-toggle-palette').textContent = state.quiz.paletteOpen
        ? '🔢 題號導覽 ▴'
        : '🔢 題號導覽 ▾';
    });

    document.getElementById('btn-quiz-submit-top').addEventListener('click', requestSubmitQuiz);
    document.getElementById('btn-quiz-submit-bottom').addEventListener('click', requestSubmitQuiz);

    document.getElementById('btn-quiz-quit').addEventListener('click', () => {
      if (confirm('確定要放棄本次測驗並返回測驗設定畫面嗎？')) {
        stopQuizTimer();
        state.quiz.stage = 'setup';
        renderQuizStage();
      }
    });

    document.getElementById('btn-quiz-prev').addEventListener('click', () => {
      if (state.quiz.currentIndex > 0) {
        state.quiz.currentIndex--;
        renderQuizRunner();
        scrollBelowHeader(document.getElementById('quiz-prompt-area'));
      }
    });

    document.getElementById('btn-quiz-next').addEventListener('click', () => {
      if (state.quiz.currentIndex < state.quiz.questions.length - 1) {
        state.quiz.currentIndex++;
        renderQuizRunner();
        scrollBelowHeader(document.getElementById('quiz-prompt-area'));
      }
    });

    document.getElementById('btn-quiz-zhuyin-backspace').addEventListener('click', backspaceQuizZhuyinSlot);
    document.getElementById('btn-quiz-zhuyin-clear').addEventListener('click', clearQuizCurrentQuestionInput);
    document.getElementById('btn-quiz-zhuyin-next').addEventListener('click', advanceOrSubmitQuizQuestion);

    const quizCharInput = document.getElementById('quiz-char-answer-input');
    const syncQuizCharInput = () => {
      const q = state.quiz.questions[state.quiz.currentIndex];
      if (!q || q.type !== 'character') return;
      const val = quizCharInput.value.trim();
      if (val) {
        state.quiz.userAnswers[q.id] = val;
      } else {
        delete state.quiz.userAnswers[q.id];
      }
      updateQuizProgressAndPalette();
    };

    quizCharInput.addEventListener('compositionstart', () => {
      isImeComposing = true;
    });
    quizCharInput.addEventListener('compositionend', () => {
      isImeComposing = false;
      syncQuizCharInput();
    });
    quizCharInput.addEventListener('input', () => {
      if (!isImeComposing) syncQuizCharInput();
    });
    quizCharInput.addEventListener('keydown', (e) => {
      if (isImeComposing) return;
      if (e.key === 'Enter') {
        e.preventDefault();
        syncQuizCharInput();
        advanceOrSubmitQuizQuestion();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        clearQuizCurrentQuestionInput();
      }
    });

    document.getElementById('btn-quiz-char-clear').addEventListener('click', () => {
      clearQuizCurrentQuestionInput();
      quizCharInput.focus();
    });
    document.getElementById('btn-quiz-char-next').addEventListener('click', () => {
      syncQuizCharInput();
      advanceOrSubmitQuizQuestion();
    });

    // 手機觸控左右滑動測驗題目區切換上下題
    const quizPromptArea = document.getElementById('quiz-prompt-area');
    if (quizPromptArea) {
      let qTouchX = 0;
      let qTouchY = 0;
      quizPromptArea.addEventListener(
        'touchstart',
        (e) => {
          if (e.touches.length === 1) {
            qTouchX = e.touches[0].clientX;
            qTouchY = e.touches[0].clientY;
          }
        },
        { passive: true }
      );
      quizPromptArea.addEventListener(
        'touchend',
        (e) => {
          if (e.changedTouches.length === 1) {
            const dx = e.changedTouches[0].clientX - qTouchX;
            const dy = e.changedTouches[0].clientY - qTouchY;
            if (Math.abs(dx) > 55 && Math.abs(dy) < 40) {
              if (dx < 0 && state.quiz.currentIndex < state.quiz.questions.length - 1) {
                state.quiz.currentIndex++;
                renderQuizRunner();
              } else if (dx > 0 && state.quiz.currentIndex > 0) {
                state.quiz.currentIndex--;
                renderQuizRunner();
              }
            }
          }
        },
        { passive: true }
      );
    }

    // 測驗結果頁面控制項
    document.getElementById('btn-quiz-retry').addEventListener('click', startQuiz);
    document.getElementById('btn-quiz-reconfig').addEventListener('click', () => {
      state.quiz.stage = 'setup';
      renderQuizStage();
    });
    document.getElementById('btn-quiz-review-wrong').addEventListener('click', () => {
      state.filters.status = 'wrong';
      document.getElementById('filter-status').value = 'wrong';
      document.querySelector('.main-nav .nav-tab[data-module="review"]').click();
    });

    document.querySelectorAll('#quiz-res-filter-group .seg-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#quiz-res-filter-group .seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
        state.quiz.resultFilter = btn.dataset.rfilter;
        renderQuizResultTable();
      });
    });

    document.getElementById('quiz-result-table-body').addEventListener('click', (e) => {
      const starBtn = e.target.closest('[data-quiz-star-id]');
      if (starBtn) {
        toggleStarQuestion(starBtn.dataset.quizStarId);
        renderQuizResultTable();
      }
    });

    // =======================================================================
    // 第三階段：紙本試卷 Word (.docx) 產生器事件綁定
    // =======================================================================
    const setDocxYears = (yearList) => {
      state.docx.selectedYears = new Set(yearList.map(Number));
      resampleDocxQuestions();
    };
    document.getElementById('btn-docx-year-all').addEventListener('click', () => setDocxYears(state.years));
    document.getElementById('btn-docx-year-recent5').addEventListener('click', () => setDocxYears(state.years.slice(-5)));
    document.getElementById('btn-docx-year-recent3').addEventListener('click', () => setDocxYears(state.years.slice(-3)));
    document.getElementById('btn-docx-year-clear').addEventListener('click', () => setDocxYears([]));

    const bindDocxOptionPills = (containerId, dataKey, stateProp, shouldResample, transformFn = (v) => v) => {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.querySelectorAll('.quiz-pill').forEach((btn) => {
        btn.addEventListener('click', () => {
          container.querySelectorAll('.quiz-pill').forEach((b) => b.classList.toggle('active', b === btn));
          state.docx[stateProp] = transformFn(btn.dataset[dataKey]);
          if (shouldResample) {
            resampleDocxQuestions();
          } else {
            updateDocxUIAndPreview();
          }
        });
      });
    };

    bindDocxOptionPills('docx-opt-type', 'dtype', 'qType', true);
    bindDocxOptionPills('docx-opt-source', 'dsource', 'qSource', true);
    bindDocxOptionPills('docx-opt-count', 'dcount', 'qCount', true, Number);

    bindDocxOptionPills('docx-opt-paper', 'dpaper', 'paperSize', false);
    bindDocxOptionPills('docx-opt-orient', 'dorient', 'orientation', false);
    bindDocxOptionPills('docx-opt-textdir', 'dtextdir', 'textDir', false);
    bindDocxOptionPills('docx-opt-bracket', 'dbracket', 'bracketStyle', false);

    const docxTitleInput = document.getElementById('docx-title-input');
    if (docxTitleInput) {
      docxTitleInput.addEventListener('input', () => {
        state.docx.title = docxTitleInput.value.trim() || '國立竹山高中 國語字音字形測驗卷（高中學生組）';
        renderDocxPaperPreview();
      });
    }

    document.querySelectorAll('#docx-preview-mode-group .seg-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#docx-preview-mode-group .seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
        state.docx.previewMode = btn.dataset.pmode;
        renderDocxPaperPreview();
      });
    });

    document.getElementById('btn-docx-resample').addEventListener('click', resampleDocxQuestions);
    document.getElementById('btn-docx-dl-student').addEventListener('click', () => generateAndDownloadDocx('student'));
    document.getElementById('btn-docx-dl-teacher').addEventListener('click', () => generateAndDownloadDocx('teacher'));
    document.getElementById('btn-docx-dl-both').addEventListener('click', () => generateAndDownloadDocx('both'));
  }

  // =========================================================================
  // 8. 啟動入口
  // =========================================================================
  async function init() {
    try {
      loadLocalStorage();
      buildVirtualKeyboard();
      buildQuizVirtualKeyboard();
      bindEvents();

      const bank = await loadQuestionBank();
      state.allQuestions = bank.questions || [];
      state.years = (bank.metadata && bank.metadata.years) || [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114];
      state.filters.selectedYears = new Set(state.years.map(Number));
      state.quiz.selectedYears = new Set(state.years.map(Number));
      state.docx.selectedYears = new Set(state.years.map(Number));

      // 建立年度複選按鈕組
      buildYearChips();
      buildQuizYearChips();
      buildDocxYearChips();
      resampleDocxQuestions();

      applyFilters();
    } catch (err) {
      console.error(err);
      alert('載入題庫時發生錯誤：' + err.message);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
