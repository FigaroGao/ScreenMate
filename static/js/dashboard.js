/**
 * ScreenMate Dashboard — displays real statistics from the backend.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;

    function fmtUptime(seconds) {
        if (!seconds) return '--';
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        var s = Math.floor(seconds % 60);
        var parts = [];
        if (h) parts.push(h + 'h');
        if (m) parts.push(m + 'm');
        parts.push(s + 's');
        return parts.join(' ');
    }

    async function refreshDashboard() {
        try {
            var data = await api.get('/api/status');
            if (!data.success) return;

            setHtml('dash-status',
                '<span class="badge bg-success">Running</span> ' +
                data.app.name + ' v' + data.app.version);

            setText('dash-uptime', fmtUptime(data.uptime_seconds));

            setText('dash-vision-calls', data.calls ? data.calls.vision : 0);
            setText('dash-chat-calls', data.calls ? data.calls.chat : 0);
            setText('dash-tts-calls', data.calls ? data.calls.tts : 0);
            setText('dash-screenshot-calls', data.calls ? (data.calls.screenshots || 0) : 0);
            setText('dash-total-calls', data.calls ? data.calls.total : 0);

            setText('dash-manual-runs', data.pipelines ? data.pipelines.manual_runs : 0);
            setText('dash-auto-runs', data.pipelines ? data.pipelines.auto_runs : 0);

            setText('dash-avg-latency', (data.avg_latency_ms || 0) + ' ms');

            if (data.last_call) {
                setText('dash-last-call',
                    data.last_call.provider_type + '/' +
                    data.last_call.provider_name + ' @ ' +
                    (data.last_call.timestamp || ''));
            } else {
                setText('dash-last-call', 'No calls yet');
            }

            setText('dash-context-msgs', data.context ? data.context.message_count : '--');
            setText('dash-log-count', data.log_count || 0);

            var provEl = document.getElementById('dash-providers');
            if (provEl && data.providers) {
                var p = [];
                for (var t in data.providers) {
                    p.push(t + ': ' + data.providers[t].join(', '));
                }
                provEl.textContent = p.join(' | ') || 'none';
            }

            document.getElementById('status-indicator').innerHTML =
                '<span class="status-dot bg-success"></span> Live';
        } catch (err) {
            console.error('Dashboard refresh failed:', err);
        }
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = String(text);
    }

    function setHtml(id, html) {
        var el = document.getElementById(id);
        if (el) el.innerHTML = html;
    }

    async function refreshHotkey() {
        try {
            var data = await api.get('/api/hotkey/status');
            if (data.success && data.hotkey) {
                setHtml('dash-hotkey', data.hotkey.shortcut || '--');
                setText('dash-hotkey-status',
                    data.hotkey.registered ? 'Active' : 'Not registered');
            }
        } catch (_) {}
    }

    refreshDashboard();
    refreshHotkey();
    setInterval(refreshDashboard, 15000);
    setInterval(refreshHotkey, 15000);
})();
