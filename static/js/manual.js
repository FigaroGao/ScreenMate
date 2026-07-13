/**
 * ScreenMate Manual Mode — vision + persona responses + history.
 */
(function () {
    'use strict';
    var api = window.ScreenMate.api;
    var escapeHtml = window.ScreenMate.escapeHtml;

    var personaSelect = document.getElementById('persona-select');
    var personaCard = document.getElementById('persona-response-card');
    var visionContent = document.getElementById('vision-content');
    var visionRendered = document.getElementById('vision-rendered');
    var visionStatus = document.getElementById('vision-status');
    var personaContent = document.getElementById('persona-content');
    var personaRendered = document.getElementById('persona-rendered');
    var personaStatus = document.getElementById('persona-status');
    var btnVisionToggle = document.getElementById('btn-toggle-vision');
    var btnPersonaToggle = document.getElementById('btn-toggle-persona');
    var historyList = document.getElementById('history-list');
    var historyCount = document.getElementById('history-count');

    var md = null;
    if (typeof markdownit !== 'undefined') {
        md = markdownit({ html: false, linkify: true, typographer: true, breaks: true,
            highlight: function (s, l) {
                if (l && window.hljs && window.hljs.getLanguage(l)) {
                    try { return '<pre class="hljs"><code>' + window.hljs.highlight(s, { language: l, ignoreIllegals: true }).value + '</code></pre>'; } catch (_) {}
                }
                return '<pre class="hljs"><code>' + escapeHtml(s) + '</code></pre>';
            },
        });
    }

    // Load persona list into dropdown
    function loadPersonas() {
        api.get('/api/personas').then(function (data) {
            if (!data.success || !data.personas) return;
            personaSelect.innerHTML = '<option value="">(Default — Vision only)</option>';
            data.personas.forEach(function (p) {
                var opt = document.createElement('option');
                opt.value = p.name;
                opt.textContent = p.name;
                personaSelect.appendChild(opt);
            });
        });
    }
    loadPersonas();

    // Update persona hint when selection changes
    personaSelect.addEventListener('change', function () {
        var name = personaSelect.value;
        if (name) {
            personaContent.textContent = 'Persona "' + name + '" selected. Press Ctrl+Shift+X to capture and analyze.';
            personaStatus.textContent = 'Ready';
            personaStatus.className = 'badge bg-secondary';
        } else {
            personaContent.textContent = 'Select a Persona above to enable styled responses.';
            personaStatus.textContent = 'No persona';
            personaStatus.className = 'badge bg-secondary';
        }
    });

    // Toggle raw/rendered
    function setupToggle(btn, contentEl, renderedEl) {
        if (!btn) return;
        var showRaw = true;
        btn.addEventListener('click', function () {
            showRaw = !showRaw;
            contentEl.style.display = showRaw ? 'block' : 'none';
            renderedEl.style.display = showRaw ? 'none' : 'block';
            btn.textContent = showRaw ? 'Rendered' : 'Raw';
        });
        btn.style.display = 'inline-block';
    }
    setupToggle(btnVisionToggle, visionContent, visionRendered);
    setupToggle(btnPersonaToggle, personaContent, personaRendered);

    function renderMarkdown(el, text) {
        el.textContent = text || '';
        if (md) {
            var rid = el.id + '-rendered';
            var r = document.getElementById(rid);
            if (r) r.innerHTML = md.render(text || '');
        }
    }

    // History render (supports vision + persona dual content)
    function renderHistory(history) {
        if (!history || !history.length) {
            historyList.innerHTML = '<p class="text-secondary text-center py-3 mb-0">No screenshots yet.</p>';
            if (historyCount) historyCount.textContent = '0 entries';
            return;
        }
        if (historyCount) historyCount.textContent = history.length + ' entries';
        var items = history.slice().reverse();
        var html = items.map(function (item, idx) {
            var id = 'hist-' + idx;
            var firstLine = (item.vision_content || item.content || '').split('\n')[0].substring(0, 80);
            if ((item.vision_content || item.content || '').length > 80) firstLine += '...';
            var personaLabel = item.persona_name ? ' | ' + escapeHtml(item.persona_name) : '';
            var vBody = md ? md.render(item.vision_content || item.content || '') : '<pre>' + escapeHtml(item.vision_content || item.content || '') + '</pre>';
            var pHtml = '';
            if (item.persona_content) {
                var pBody = md ? md.render(item.persona_content) : '<pre>' + escapeHtml(item.persona_content) + '</pre>';
                pHtml = '<hr class="border-secondary my-2"><div class="small text-info fw-semibold mb-1">Persona Response</div><div class="markdown-body small">' + pBody + '</div>';
            }
            return '<div class="history-item border-bottom border-secondary">' +
                '<div class="history-header px-3 py-2 d-flex align-items-center gap-2" style="cursor:pointer;" onclick="var b=this.nextElementSibling;b.classList.toggle(\'d-none\')">' +
                '<i class="bi bi-chevron-right small text-secondary history-chevron"></i>' +
                '<span class="text-secondary small">' + escapeHtml(item.timestamp) + '</span>' +
                '<span class="badge bg-secondary">' + escapeHtml(item.source) + '</span>' +
                '<span class="text-truncate small">' + escapeHtml(firstLine) + '</span>' +
                '<span class="text-secondary small text-nowrap ms-auto">' + escapeHtml(item.vision_model || '') + personaLabel + ' ' + (item.latency_ms || '') + 'ms</span>' +
                '</div>' +
                '<div id="' + id + '" class="history-body px-3 pb-2 d-none">' +
                '<div class="small text-info fw-semibold mb-1">Vision</div>' +
                '<div class="markdown-body small">' + vBody + '</div>' +
                pHtml +
                '</div></div>';
        }).join('');
        historyList.innerHTML = html;
    }

    // Poll pipeline status
    var lastRunCount = -1;
    var lastHistoryLen = 0;

    async function poll() {
        try {
            var data = await api.get('/api/pipeline/status');
            if (!data.success || !data.pipeline) return;
            var p = data.pipeline;

            if (p.pipeline_runs !== lastRunCount && p.last_result) {
                var r = p.last_result;
                var vis = r.vision || {};
                renderMarkdown(visionContent, vis.content || r.message || '');
                visionStatus.textContent = (vis.model || '') + ' (' + (r.processing_time_ms || '?') + 'ms)';
                visionStatus.className = 'badge bg-info';

                var chat = r.chat || {};
                if (chat.content) {
                    renderMarkdown(personaContent, chat.content);
                    personaStatus.textContent = (chat.model || '') + ' (' + (chat.latency_ms || '?') + 'ms)';
                    personaStatus.className = 'badge bg-success';
                } else if (r.persona) {
                    personaContent.textContent = '(Chat provider returned no content)';
                    personaStatus.textContent = 'No response';
                    personaStatus.className = 'badge bg-secondary';
                } else {
                    personaContent.textContent = 'Select a Persona above to enable styled responses.';
                }
                lastRunCount = p.pipeline_runs;
            }

            if (p.running) {
                visionStatus.textContent = p.progress === 'capturing' ? 'Capturing...' : 'Analyzing...';
                visionStatus.className = 'badge bg-warning';
            }

            if (p.history && p.history.length !== lastHistoryLen) {
                renderHistory(p.history);
                lastHistoryLen = p.history.length;
                // Update persona hint based on latest history
                var last = p.history[p.history.length - 1];
                if (last && last.persona_name && personaSelect.value) {
                    // Don't overwrite if we already have real content
                } else if (personaSelect.value) {
                    personaContent.textContent = 'Persona "' + personaSelect.value + '" selected. Press Ctrl+Shift+X to capture and analyze.';
                }
            }
        } catch (_) {}
    }

    poll();
    setInterval(poll, 800);
})();
