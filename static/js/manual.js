/**
 * ScreenMate Manual Mode — displays pipeline results + screenshot history.
 * Polls /api/pipeline/status for live updates.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var escapeHtml = window.ScreenMate.escapeHtml;

    var responseContent = document.getElementById('response-content');
    var responseRendered = document.getElementById('response-rendered');
    var responseStatus = document.getElementById('response-status');
    var btnToggleView = document.getElementById('btn-toggle-view');
    var historyList = document.getElementById('history-list');
    var historyCount = document.getElementById('history-count');

    // --- markdown-it ---
    var md = null;
    if (typeof markdownit !== 'undefined') {
        md = markdownit({
            html: false, linkify: true, typographer: true, breaks: true,
            highlight: function (str, lang) {
                if (lang && window.hljs && window.hljs.getLanguage(lang)) {
                    try {
                        return '<pre class="hljs"><code>' +
                            window.hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                            '</code></pre>';
                    } catch (_) {}
                }
                return '<pre class="hljs"><code>' + escapeHtml(str) + '</code></pre>';
            },
        });
    }

    var showRendered = false;

    // --- Toggle raw/rendered ---
    if (btnToggleView) {
        btnToggleView.addEventListener('click', function () {
            showRendered = !showRendered;
            responseContent.style.display = showRendered ? 'none' : 'block';
            responseRendered.style.display = showRendered ? 'block' : 'none';
            btnToggleView.textContent = showRendered ? 'Raw' : 'Rendered';
        });
    }

    // --- Render markdown into response area ---
    function renderResponse(text, model, latency) {
        responseContent.textContent = text || '(empty)';
        responseStatus.textContent = (model || '') + ' (' + (latency || '?') + 'ms)';
        responseStatus.className = 'badge bg-success';
        if (md) {
            responseRendered.innerHTML = md.render(text || '');
            btnToggleView.style.display = 'inline-block';
        }
        // Default to raw view
        showRendered = false;
        responseContent.style.display = 'block';
        responseRendered.style.display = 'none';
        if (btnToggleView) btnToggleView.textContent = 'Rendered';
    }

    // --- Build history list ---
    function renderHistory(history) {
        if (!history || !history.length) {
            historyList.innerHTML = '<p class="text-secondary text-center py-3 mb-0">No screenshots yet.</p>';
            if (historyCount) historyCount.textContent = '0 entries';
            return;
        }
        if (historyCount) historyCount.textContent = history.length + ' entries';

        // Show newest first
        var items = history.slice().reverse();
        var html = '';
        items.forEach(function (item, idx) {
            var id = 'hist-' + idx;
            var firstLine = (item.content || '').split('\n')[0].substring(0, 100);
            if ((item.content || '').length > 100) firstLine += '...';
            html += (
                '<div class="history-item border-bottom border-secondary">' +
                '  <div class="history-header px-3 py-2 d-flex align-items-center gap-2" ' +
                '       style="cursor:pointer;" onclick="document.getElementById(\'' + id + '\').classList.toggle(\'d-none\')">' +
                '    <i class="bi bi-chevron-right small text-secondary history-chevron"></i>' +
                '    <span class="text-secondary small">' + escapeHtml(item.timestamp) + '</span>' +
                '    <span class="badge bg-secondary">' + escapeHtml(item.source) + '</span>' +
                '    <span class="text-truncate small" style="flex:1;">' + escapeHtml(firstLine) + '</span>' +
                '    <span class="text-secondary small text-nowrap">' + escapeHtml(item.model) + ' ' + (item.latency_ms || 0) + 'ms</span>' +
                '  </div>' +
                '  <div id="' + id + '" class="history-body px-3 pb-2 d-none">' +
                '    <div class="markdown-body small">' + (md ? md.render(item.content || '') : '<pre>' + escapeHtml(item.content || '') + '</pre>') + '</div>' +
                '  </div>' +
                '</div>'
            );
        });
        historyList.innerHTML = html;
    }

    // --- Poll pipeline status ---
    var lastRunCount = -1;
    var lastHistoryLen = 0;

    async function poll() {
        try {
            var data = await api.get('/api/pipeline/status');
            if (!data.success || !data.pipeline) return;

            var p = data.pipeline;

            // New result arrived?
            if (p.pipeline_runs !== lastRunCount && p.last_result) {
                var r = p.last_result;
                var vis = r.vision || {};
                renderResponse(vis.content || r.message || '', vis.model || '', r.processing_time_ms || 0);
                lastRunCount = p.pipeline_runs;
            }

            // History changed?
            if (p.history && p.history.length !== lastHistoryLen) {
                renderHistory(p.history);
                lastHistoryLen = p.history.length;
            }

            // Show progress
            if (p.running) {
                responseStatus.textContent = p.progress === 'capturing' ? 'Capturing...' : 'Analyzing...';
                responseStatus.className = 'badge bg-info';
            }
        } catch (_) {}
    }

    // --- Init ---
    poll();
    setInterval(poll, 800);
})();
