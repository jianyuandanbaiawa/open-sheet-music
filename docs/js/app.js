(function () {
    'use strict';

    const CACHE_KEY = 'adofai_chart_index';
    const CACHE_TTL = 5 * 60 * 1000;

    const state = {
        charts: [],
        filtered: [],
        search: '',
        filters: {
            difficulty: 'all',
            platform: 'all',
        },
        sort: 'date-desc',
    };

    async function loadCharts() {
        try {
            const cached = getCache();
            if (cached) {
                state.charts = cached.charts;
                updateStats(cached);
                return;
            }

            const response = await fetch('./charts/index.json?t=' + Date.now());
            if (!response.ok) {
                throw new Error('Failed to load charts index');
            }

            const data = await response.json();
            state.charts = data.charts || [];
            setCache(data);
            updateStats(data);
        } catch (err) {
            console.warn('加载谱子索引失败，使用示例数据:', err);
            state.charts = getSampleCharts();
            updateStats({ total_charts: state.charts.length, last_updated: new Date().toISOString() });
        }
    }

    function getCache() {
        try {
            const raw = localStorage.getItem(CACHE_KEY);
            if (!raw) return null;
            const data = JSON.parse(raw);
            if (Date.now() - data.timestamp > CACHE_TTL) return null;
            return data;
        } catch {
            return null;
        }
    }

    function setCache(data) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({
                timestamp: Date.now(),
                charts: data.charts,
                total_charts: data.total_charts,
                last_updated: data.last_updated,
            }));
        } catch {}
    }

    function updateStats(data) {
        const total = data.total_charts || state.charts.length;
        const platforms = new Set(state.charts.map(c => c.source?.platform).filter(Boolean));

        document.getElementById('stat-total').textContent = total;
        document.getElementById('stat-platforms').textContent = platforms.size;

        const updated = data.last_updated;
        if (updated) {
            const d = new Date(updated);
            document.getElementById('stat-updated').textContent =
                `${d.getMonth() + 1}/${d.getDate()}`;
        }
    }

    function getSampleCharts() {
        return [
            {
                id: 'sample01',
                title: '示例谱子 - Rhapsody',
                artist: 'Hafiz Azman',
                chart_author: '社区谱师',
                difficulty: 8,
                bpm: 140,
                download_date: '2026-08-01T10:00:00Z',
                source: { platform: 'bilibili', url: 'https://www.bilibili.com/' },
                tags: ['官方', '进阶'],
                has_music: true,
                has_preview: true,
                file_path: 'charts/sample01/chart.adofai',
            },
            {
                id: 'sample02',
                title: '示例谱子 - Prelude',
                artist: 'Jade Kim',
                chart_author: '社区谱师',
                difficulty: 5,
                bpm: 120,
                download_date: '2026-07-28T14:00:00Z',
                source: { platform: 'douyin', url: 'https://www.douyin.com/' },
                tags: ['入门'],
                has_music: true,
                has_preview: true,
                file_path: 'charts/sample02/chart.adofai',
            },
        ];
    }

    function applyFilters() {
        let result = [...state.charts];

        if (state.search) {
            const q = state.search.toLowerCase();
            result = result.filter(c =>
                (c.title || '').toLowerCase().includes(q) ||
                (c.artist || '').toLowerCase().includes(q) ||
                (c.chart_author || '').toLowerCase().includes(q) ||
                (c.tags || []).some(t => t.toLowerCase().includes(q))
            );
        }

        if (state.filters.difficulty !== 'all') {
            const diff = parseInt(state.filters.difficulty);
            if (state.filters.difficulty === '9') {
                result = result.filter(c => (c.difficulty || 0) >= 9);
            } else {
                result = result.filter(c => (c.difficulty || 0) === diff);
            }
        }

        if (state.filters.platform !== 'all') {
            result = result.filter(c =>
                (c.source?.platform || '') === state.filters.platform
            );
        }

        result.sort((a, b) => {
            switch (state.sort) {
                case 'date-asc':
                    return (a.download_date || '').localeCompare(b.download_date || '');
                case 'difficulty-desc':
                    return (b.difficulty || 0) - (a.difficulty || 0);
                case 'difficulty-asc':
                    return (a.difficulty || 0) - (b.difficulty || 0);
                case 'title-asc':
                    return (a.title || '').localeCompare(b.title || '');
                case 'artist-asc':
                    return (a.artist || '').localeCompare(b.artist || '');
                default:
                    return (b.download_date || '').localeCompare(a.download_date || '');
            }
        });

        state.filtered = result;
        renderCharts();
    }

    function renderCharts() {
        const grid = document.getElementById('chart-grid');
        const empty = document.getElementById('empty-state');
        const count = document.getElementById('result-count');

        count.textContent = state.filtered.length + ' 个结果';

        if (!state.filtered.length) {
            grid.innerHTML = '';
            empty.style.display = 'block';
            return;
        }

        empty.style.display = 'none';

        grid.innerHTML = state.filtered.map(chart => `
            <div class="chart-card" data-id="${chart.id}">
                <div class="chart-preview">
                    <div class="chart-preview-icon">${getPreviewIcon(chart)}</div>
                    <div class="chart-preview-wave">
                        ${getWaveBars()}
                    </div>
                </div>
                <div class="chart-body">
                    <h3 class="chart-title">${escapeHtml(chart.title || '未知曲目')}</h3>
                    <p class="chart-artist">${escapeHtml(chart.artist || '')}</p>
                    <div class="chart-meta">
                        ${chart.difficulty ? `<span class="chart-tag difficulty">Lv.${chart.difficulty}</span>` : ''}
                        ${chart.source?.platform ? `<span class="chart-tag platform">${getPlatformIcon(chart.source.platform)} ${getPlatformName(chart.source.platform)}</span>` : ''}
                        ${chart.has_music ? '<span class="chart-tag">🎵 音乐</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');

        grid.querySelectorAll('.chart-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                const chart = state.charts.find(c => c.id === id);
                if (chart) openModal(chart);
            });
        });
    }

    function openModal(chart) {
        const modal = document.getElementById('chart-modal');
        const body = document.getElementById('modal-body');

        const sourceUrl = chart.source?.url || '';
        const fileName = `chart_${chart.id}.adofai`;

        body.innerHTML = `
            <div class="modal-preview">${getPreviewIcon(chart)}</div>
            <h2 class="modal-title">${escapeHtml(chart.title || '未知曲目')}</h2>
            <p class="modal-artist">${escapeHtml(chart.artist || '未知艺术家')}</p>
            <div class="modal-info-grid">
                <div class="modal-info-item">
                    <div class="modal-info-label">谱师</div>
                    <div class="modal-info-value">${escapeHtml(chart.chart_author || '未知')}</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">难度</div>
                    <div class="modal-info-value">${chart.difficulty ? 'Lv.' + chart.difficulty : '--'}</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">BPM</div>
                    <div class="modal-info-value">${chart.bpm || '--'}</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">平台</div>
                    <div class="modal-info-value">${getPlatformName(chart.source?.platform || '')}</div>
                </div>
                ${chart.download_date ? `
                <div class="modal-info-item">
                    <div class="modal-info-label">上传日期</div>
                    <div class="modal-info-value">${formatDate(chart.download_date)}</div>
                </div>` : ''}
                ${chart.has_music ? `
                <div class="modal-info-item">
                    <div class="modal-info-label">音乐</div>
                    <div class="modal-info-value">✅ 已包含</div>
                </div>` : ''}
            </div>
            ${sourceUrl ? `
            <div class="modal-section-title">原始链接</div>
            <div style="margin-bottom: 16px;">
                <a href="${sourceUrl}" target="_blank" class="btn btn-secondary">
                    🔗 访问原帖
                </a>
            </div>` : ''}
            <div class="modal-actions">
                <a href="${chart.file_path || '#'}" download="${fileName}" class="btn btn-primary" ${chart.file_path ? '' : 'style="display:none"'}>
                    ⬇ 下载谱子
                </a>
                <button class="btn btn-secondary" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(chart).replace(/"/g, '&quot;')}, null, 2))">
                    📋 复制元数据
                </button>
            </div>
        `;

        modal.classList.add('visible');
    }

    function closeModal() {
        document.getElementById('chart-modal').classList.remove('visible');
    }

    function getPreviewIcon(chart) {
        if (chart.has_music) return '🎵';
        if ((chart.difficulty || 0) >= 8) return '🔥';
        if ((chart.difficulty || 0) >= 5) return '⚡';
        return '🎮';
    }

    function getWaveBars() {
        let html = '';
        for (let i = 0; i < 20; i++) {
            const delay = (i * 0.1).toFixed(1);
            html += `<span style="animation-delay: ${delay}s"></span>`;
        }
        return html;
    }

    function getPlatformIcon(platform) {
        const icons = { bilibili: '📺', douyin: '🎵', kuaishou: '⚡', forum: '💬' };
        return icons[platform] || '🌐';
    }

    function getPlatformName(platform) {
        const names = { bilibili: 'B站', douyin: '抖音', kuaishou: '快手', forum: '论坛' };
        return names[platform] || platform || '未知';
    }

    function formatDate(iso) {
        try {
            const d = new Date(iso);
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        } catch {
            return iso;
        }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function bindEvents() {
        const searchInput = document.getElementById('search-input');
        const searchClear = document.getElementById('search-clear');

        searchInput.addEventListener('input', (e) => {
            state.search = e.target.value;
            searchClear.classList.toggle('visible', !!state.search);
            applyFilters();
        });

        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            state.search = '';
            searchClear.classList.remove('visible');
            applyFilters();
            searchInput.focus();
        });

        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const filter = chip.dataset.filter;
                const value = chip.dataset.value;

                document.querySelectorAll(`.chip[data-filter="${filter}"]`).forEach(c => c.classList.remove('active'));
                chip.classList.add('active');

                state.filters[filter] = value;
                applyFilters();
            });
        });

        document.getElementById('sort-select').addEventListener('change', (e) => {
            state.sort = e.target.value;
            applyFilters();
        });

        document.getElementById('modal-close').addEventListener('click', closeModal);
        document.querySelector('.modal-backdrop').addEventListener('click', closeModal);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });

        document.getElementById('api-link').addEventListener('click', (e) => {
            e.preventDefault();
            window.open('./charts/index.json', '_blank');
        });

        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const view = link.dataset.view;
                if (view === 'about') {
                    e.preventDefault();
                    alert('ADOFAI Chart Hub\n\n冰与火之舞社区谱库\n\n收录来自各平台的自制谱子，由社区爬虫自动抓取。');
                }
            });
        });
    }

    function init() {
        bindEvents();
        loadCharts().then(() => {
            applyFilters();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
