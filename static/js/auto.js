/**
 * ScreenMate Auto Mode — start/stop background monitoring.
 * Uses ApiClient, Toast notifications.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;

    var btnStart = document.getElementById('btn-auto-start');
    var btnStop = document.getElementById('btn-auto-stop');
    var intervalSlider = document.getElementById('auto-interval');
    var intervalLabel = document.getElementById('interval-label');
    var runningStatus = document.getElementById('auto-running-status');
    var shotCount = document.getElementById('auto-shot-count');
    var lastShot = document.getElementById('auto-last-shot');
    var elapsed = document.getElementById('auto-elapsed');

    var pollTimer = null;

    intervalSlider.addEventListener('input', function () {
        intervalLabel.textContent = this.value + 's';
    });

    btnStart.addEventListener('click', async function () {
        btnLoading(btnStart, 'Starting...');
        try {
            var data = await api.post('/api/auto/start', {
                interval: parseInt(intervalSlider.value),
            });
            if (data.success) {
                setRunning(true);
                startPolling();
                toast(data.message, 'success');
            } else {
                toast(data.message || data.error, 'warning');
            }
        } catch (err) {
            toast(err.message, 'danger');
        } finally {
            btnRestore(btnStart);
        }
    });

    btnStop.addEventListener('click', async function () {
        btnLoading(btnStop, 'Stopping...');
        try {
            var data = await api.post('/api/auto/stop');
            if (data.success) {
                setRunning(false);
                stopPolling();
                toast(data.message, 'success');
            } else {
                toast(data.message || data.error, 'warning');
            }
        } catch (err) {
            toast(err.message, 'danger');
        } finally {
            btnRestore(btnStop);
        }
    });

    function setRunning(running) {
        btnStart.disabled = running;
        btnStop.disabled = !running;
        runningStatus.textContent = running ? 'Running' : 'Stopped';
        runningStatus.className = running ? 'badge bg-success' : 'badge bg-secondary';
        if (!running) {
            elapsed.textContent = '--';
            shotCount.textContent = '0';
            lastShot.textContent = 'never';
        }
    }

    async function pollStatus() {
        try {
            var data = await api.get('/api/auto/status');
            if (data.data && data.data.monitor_status) {
                var ms = data.data.monitor_status;
                if (ms.running) {
                    shotCount.textContent = ms.screenshot_count;
                    lastShot.textContent = ms.last_screenshot_iso;
                    var secs = Math.floor(ms.elapsed_seconds);
                    var m = Math.floor(secs / 60);
                    var s = secs % 60;
                    elapsed.textContent = m + 'm ' + s + 's';
                } else {
                    setRunning(false);
                    stopPolling();
                }
            }
        } catch (_) { /* ignore poll errors */ }
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(pollStatus, 2000);
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }
})();
