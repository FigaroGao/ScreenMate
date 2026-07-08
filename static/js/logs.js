/**
 * ScreenMate Logs — refresh, clear, search.
 * Uses ApiClient, Toast notifications.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;
    var escapeHtml = window.ScreenMate.escapeHtml;

    var tbody = document.getElementById('logs-tbody');
    var btnRefresh = document.getElementById('btn-refresh-logs');
    var btnClear = document.getElementById('btn-clear-logs');
    var searchInput = document.getElementById('log-search');

    function levelBadge(level) {
        var map = {
            'DEBUG': 'bg-secondary',
            'INFO': 'bg-info text-dark',
            'WARNING': 'bg-warning text-dark',
            'ERROR': 'bg-danger',
            'CRITICAL': 'bg-danger',
        };
        var cls = map[level] || 'bg-secondary';
        return '<span class="badge ' + cls + '">' + level + '</span>';
    }

    async function loadLogs() {
        try {
            var data = await api.get('/api/logs?count=200');
            if (!data.success || !data.logs.length) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary">No logs yet.</td></tr>';
                return;
            }
            var searchTerm = searchInput.value.toLowerCase();
            var filtered = data.logs.filter(function (log) {
                if (!searchTerm) return true;
                return (
                    log.message.toLowerCase().includes(searchTerm) ||
                    log.module.toLowerCase().includes(searchTerm) ||
                    log.level.toLowerCase().includes(searchTerm)
                );
            });
            tbody.innerHTML = filtered.map(function (log) {
                return (
                    '<tr>' +
                    '<td class="text-secondary small">' + escapeHtml(log.timestamp) + '</td>' +
                    '<td>' + levelBadge(log.level) + '</td>' +
                    '<td class="text-secondary small">' + escapeHtml(log.module) + '</td>' +
                    '<td>' + escapeHtml(log.message) + '</td>' +
                    '</tr>'
                );
            }).join('');
        } catch (err) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-danger">Failed to load logs: ' + err.message + '</td></tr>';
        }
    }

    btnRefresh.addEventListener('click', async function () {
        btnLoading(btnRefresh, 'Refreshing...');
        try {
            await loadLogs();
            toast('Logs refreshed', 'info');
        } finally {
            btnRestore(btnRefresh);
        }
    });

    btnClear.addEventListener('click', async function () {
        if (!confirm('Clear all logs?')) return;
        btnLoading(btnClear, 'Clearing...');
        try {
            await api.post('/api/logs/clear');
            await loadLogs();
            toast('Logs cleared', 'success');
        } catch (err) {
            toast(err.message, 'danger');
        } finally {
            btnRestore(btnClear);
        }
    });

    searchInput.addEventListener('input', loadLogs);

    loadLogs();
})();
