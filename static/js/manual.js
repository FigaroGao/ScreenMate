/**
 * ScreenMate Manual Mode — screenshot -> vision -> markdown response.
 * Uses ApiClient, Toast notifications, loading states, markdown-it.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;

    var btnFullscreen = document.getElementById('btn-fullscreen');
    var btnSend = document.getElementById('btn-send');
    var btnToggleView = document.getElementById('btn-toggle-view');
    var promptEl = document.getElementById('manual-prompt');
    var visionProvider = document.getElementById('vision-provider');
    var promptTemplate = document.getElementById('prompt-template');
    var responseContent = document.getElementById('response-content');
    var responseRendered = document.getElementById('response-rendered');
    var responseStatus = document.getElementById('response-status');
    var processingCard = document.getElementById('processing-card');
    var processingText = document.getElementById('processing-text');

    // Initialize markdown-it if available
    var md = null;
    if (typeof markdownit !== 'undefined') {
        md = markdownit({
            html: false,
            linkify: true,
            typographer: true,
            breaks: true,
            highlight: function (str, lang) {
                if (lang && window.hljs && window.hljs.getLanguage(lang)) {
                    try {
                        return '<pre class="hljs"><code>' +
                            window.hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                            '</code></pre>';
                    } catch (_) {}
                }
                return '<pre class="hljs"><code>' + ScreenMate.escapeHtml(str) + '</code></pre>';
            },
        });
    }

    var showRaw = true;

    function toggleView() {
        showRaw = !showRaw;
        responseContent.style.display = showRaw ? 'block' : 'none';
        responseRendered.style.display = showRaw ? 'none' : 'block';
        btnToggleView.innerHTML = showRaw ?
            '<i class="bi bi-markdown"></i> Rendered' :
            '<i class="bi bi-file-earmark-code"></i> Raw';
    }

    if (btnToggleView) {
        btnToggleView.addEventListener('click', toggleView);
    }

    /**
     * Render markdown content.
     * @param {string} text
     */
    function renderResponse(text) {
        responseContent.textContent = text;
        if (md) {
            responseRendered.innerHTML = md.render(text);
            btnToggleView.style.display = 'inline-block';
            // Show rendered by default if markdown has structured content
            if (text.indexOf('```') !== -1 || text.indexOf('##') !== -1 || text.indexOf('|') !== -1) {
                if (showRaw) toggleView();
            }
        } else {
            responseRendered.innerHTML = '<p class="text-secondary">markdown-it not loaded</p>';
        }
    }

    /**
     * Execute a manual mode request.
     * @param {string} screenshotType
     */
    async function handleSend(screenshotType) {
        var btn = screenshotType === 'fullscreen' ? btnFullscreen : btnSend;
        btnLoading(btn || btnSend, 'Processing...');
        btnLoading(btnSend, 'Processing...');

        processingCard.style.display = 'block';
        processingText.textContent = 'Capturing screen...';
        responseStatus.textContent = 'Processing';
        responseStatus.className = 'badge bg-info';
        responseContent.textContent = 'Taking screenshot...';

        var visionName = visionProvider.value;
        if (visionName === 'openai') {
            processingText.textContent = 'Calling vision API (this may take a few seconds)...';
        }

        try {
            var data = await api.post('/api/manual', {
                prompt: promptEl.value.trim(),
                template_id: promptTemplate.value,
                screenshot_type: screenshotType,
                vision_provider: visionName,
                enable_tts: false,
            });

            processingCard.style.display = 'none';

            if (data.success) {
                var latency = data.processing_time_ms || 0;
                var model = (data.vision && data.vision.model) || 'unknown';
                responseStatus.textContent = model + ' (' + latency + 'ms)';
                responseStatus.className = 'badge bg-success';

                var visionContent = (data.vision && data.vision.content) || '';
                if (visionContent) {
                    renderResponse(visionContent);
                } else {
                    responseContent.textContent = JSON.stringify(data, null, 2);
                }

                toast('Analyzed in ' + latency + 'ms with ' + model, 'success');
            } else {
                responseStatus.textContent = 'Error';
                responseStatus.className = 'badge bg-danger';
                var errMsg = data.error || 'Unknown error';
                responseContent.textContent = errMsg;
                toast(errMsg, 'danger');
            }
        } catch (err) {
            processingCard.style.display = 'none';
            responseStatus.textContent = 'Error';
            responseStatus.className = 'badge bg-danger';
            responseContent.textContent = 'Request failed: ' + err.message;
            toast(err.message, 'danger');
        } finally {
            btnRestore(btn);
            btnRestore(btnSend);
        }
    }

    btnFullscreen.addEventListener('click', function () { handleSend('fullscreen'); });
    btnSend.addEventListener('click', function () { handleSend('fullscreen'); });

    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'A') {
            e.preventDefault();
            handleSend('fullscreen');
        }
    });
})();
