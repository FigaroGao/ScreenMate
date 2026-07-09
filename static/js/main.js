/**
 * ScreenMate — global utilities: ApiClient, Toast, Loading overlay.
 *
 * All page-specific scripts use `ScreenMate.api` for HTTP and
 * `ScreenMate.toast` for notifications instead of raw `fetch` and `alert()`.
 */

(function () {
    'use strict';

    // ==================================================================
    // ApiClient
    // ==================================================================

    /**
     * Unified HTTP client for the ScreenMate frontend.
     *
     * Usage:
     *   const data = await ScreenMate.api.get('/api/status');
     *   const result = await ScreenMate.api.post('/api/manual', { prompt: 'hi' });
     */
    class ApiClient {
        /**
         * Perform a GET request.
         * @param {string} url
         * @returns {Promise<object>}
         */
        async get(url) {
            const resp = await fetch(url, {
                headers: { 'Content-Type': 'application/json' },
            });
            return this._handleResponse(resp);
        }

        /**
         * Perform a POST request.
         * @param {string} url
         * @param {object} [body]
         * @returns {Promise<object>}
         */
        async post(url, body) {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: body ? JSON.stringify(body) : undefined,
            });
            return this._handleResponse(resp);
        }

        /**
         * @param {Response} resp
         * @returns {Promise<object>}
         */
        async _handleResponse(resp) {
            if (!resp.ok) {
                const text = await resp.text().catch(function () { return ''; });
                throw new Error('HTTP ' + resp.status + ': ' + (text || resp.statusText));
            }
            return resp.json();
        }
    }

    // ==================================================================
    // Toast Notification System
    // ==================================================================

    /**
     * Show a Bootstrap toast notification.
     *
     * @param {string} message  - The message text.
     * @param {'success'|'danger'|'warning'|'info'} [type='info'] - Toast type.
     * @param {string} [title]  - Optional title.
     */
    function showToast(message, type, title) {
        type = type || 'info';

        var icons = {
            success: 'bi-check-circle-fill text-success',
            danger: 'bi-exclamation-triangle-fill text-danger',
            warning: 'bi-exclamation-circle-fill text-warning',
            info: 'bi-info-circle-fill text-info',
        };
        var icon = icons[type] || icons.info;

        var titles = {
            success: title || 'Success',
            danger: title || 'Error',
            warning: title || 'Warning',
            info: title || 'Info',
        };

        var container = document.getElementById('toast-container');
        if (!container) return;

        var toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);

        var html = (
            '<div id="' + toastId + '" class="toast align-items-center border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">' +
            '  <div class="d-flex">' +
            '    <div class="toast-body d-flex align-items-center gap-2">' +
            '      <i class="' + icon + ' fs-5"></i>' +
            '      <div>' +
            '        <strong class="me-1">' + escapeHtml(titles[type]) + '</strong>' +
            '        <span class="text-secondary">' + escapeHtml(message) + '</span>' +
            '      </div>' +
            '    </div>' +
            '    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
            '  </div>' +
            '</div>'
        );

        container.insertAdjacentHTML('beforeend', html);
        var toastEl = document.getElementById(toastId);
        if (toastEl && window.bootstrap) {
            var toast = new bootstrap.Toast(toastEl, { delay: 4000 });
            toast.show();
            toastEl.addEventListener('hidden.bs.toast', function () {
                toastEl.remove();
            });
        }
    }

    // ==================================================================
    // Global Loading Overlay
    // ==================================================================

    /**
     * Show/hide the global loading spinner.
     * @param {boolean} show
     * @param {string} [text='Processing...']
     */
    function setLoading(show, text) {
        var overlay = document.getElementById('global-loading');
        var label = document.getElementById('global-loading-text');
        if (!overlay) return;
        if (show) {
            if (label && text) label.textContent = text;
            overlay.style.display = 'flex';
        } else {
            overlay.style.display = 'none';
        }
    }

    // ==================================================================
    // Button loading state helpers
    // ==================================================================

    /**
     * Set a button to loading state.
     * @param {HTMLElement} btn
     * @param {string} [text='Loading...']
     */
    function btnLoading(btn, text) {
        if (!btn) return;
        btn._originalHTML = btn._originalHTML || btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>' + (text || 'Loading...');
    }

    /**
     * Restore a button from loading state.
     * @param {HTMLElement} btn
     */
    function btnRestore(btn) {
        if (!btn) return;
        btn.disabled = false;
        if (btn._originalHTML) {
            btn.innerHTML = btn._originalHTML;
            delete btn._originalHTML;
        }
    }

    // ==================================================================
    // Utility
    // ==================================================================

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // ==================================================================
    // Server time updater
    // ==================================================================

    function updateServerTime() {
        var el = document.getElementById('server-time');
        if (el) {
            el.textContent = new Date().toLocaleTimeString();
        }
    }
    updateServerTime();
    setInterval(updateServerTime, 10000);

    // ==================================================================
    // Pipeline state polling (shared by manual, hotkey, auto)
    // ==================================================================
    var _lastRunCount = null;   // null = not yet initialised
    var _wasRunning = false;

    async function pollPipelineState() {
        try {
            var data = await window.ScreenMate.api.get('/api/pipeline/status');
            if (!data.success) return;

            var p = data.pipeline;

            // First poll after page load: sync to current state, no toast
            if (_lastRunCount === null) {
                _lastRunCount = p.pipeline_runs;
                _wasRunning = p.running;
                return;
            }

            // --- New pipeline started (transition to running) ---
            if (p.running && !_wasRunning) {
                window.ScreenMate.toast('Capturing & analyzing...', 'info');
            }
            _wasRunning = p.running;

            // --- Pipeline finished (runCount changed) ---
            if (p.pipeline_runs !== _lastRunCount && p.pipeline_runs > 0) {
                if (p.progress === 'completed') {
                    var lat = p.last_result ? (p.last_result.processing_time_ms || '?') : '?';
                    window.ScreenMate.toast('Screenshot analyzed in ' + lat + 'ms', 'success');
                } else if (p.progress === 'failed') {
                    window.ScreenMate.toast(p.last_error || 'Pipeline failed', 'danger');
                }
                _lastRunCount = p.pipeline_runs;
            }

        } catch (_) {}
    }

    // Start polling at 500ms
    setInterval(pollPipelineState, 500);

    // ==================================================================
    // Export to global
    // ==================================================================

    window.ScreenMate = window.ScreenMate || {};
    window.ScreenMate.api = new ApiClient();
    window.ScreenMate.toast = showToast;
    window.ScreenMate.loading = setLoading;
    window.ScreenMate.btnLoading = btnLoading;
    window.ScreenMate.btnRestore = btnRestore;
    window.ScreenMate.escapeHtml = escapeHtml;
})();
