/**
 * ScreenMate Settings — auto-load, save, reset, test connection.
 */

(function () {
    'use strict';

    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;

    var form = document.getElementById('settings-form');
    var btnTest = document.getElementById('btn-test-connection');
    var btnTestChat = document.getElementById('btn-test-chat');
    var btnSave = document.getElementById('btn-save-settings');
    var btnReset = document.getElementById('btn-reset-settings');

    // ==================================================================
    // 1. Load current settings on page open
    // ==================================================================
    async function loadSettings() {
        try {
            var data = await api.get('/api/settings');
            if (!data.success || !data.settings) return;

            var s = data.settings;
            // Fill each form field by name if it exists in the response
            var fields = form.querySelectorAll('[name]');
            fields.forEach(function (el) {
                var key = el.getAttribute('name');
                if (s[key] !== undefined) {
                    var val = s[key];
                    // Don't fill masked API key placeholders
                    if (val === '***') val = '';
                    if (el.type === 'checkbox') {
                        el.checked = (val === true || val === 'true');
                    } else {
                        el.value = val;
                    }
                }
            });
        } catch (err) {
            console.warn('Failed to load settings:', err);
        }
    }

    loadSettings();

    // ==================================================================
    // 2. Test Connection (real for vision providers)
    // ==================================================================
    if (btnTest) {
        btnTest.addEventListener('click', async function () {
            var provSelect = document.getElementById('vision-provider-select');
            var provName = provSelect ? provSelect.value : 'mock';
            btnLoading(btnTest, 'Testing...');
            try {
                var data = await api.post('/api/provider/test', {
                    type: 'vision', provider: provName,
                });
                toast(data.message, data.success ? 'success' : 'danger',
                      data.success ? 'Vision OK' : 'Vision Failed');
            } catch (err) { toast(err.message, 'danger'); }
            finally { btnRestore(btnTest); }
        });
    }

    // Test Chat Connection
    if (btnTestChat) {
        btnTestChat.addEventListener('click', async function () {
            var provSelect = document.getElementById('chat-provider-select');
            var provName = provSelect ? provSelect.value : 'mock';
            btnLoading(btnTestChat, 'Testing...');
            try {
                var data = await api.post('/api/provider/test', {
                    type: 'chat', provider: provName,
                });
                toast(data.message, data.success ? 'success' : 'danger',
                      data.success ? 'Chat OK' : 'Chat Failed');
            } catch (err) { toast(err.message, 'danger'); }
            finally { btnRestore(btnTestChat); }
        });
    }

    // ==================================================================
    // 3. Save Settings
    // ==================================================================
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            // Build payload from all named fields
            var formData = new FormData(form);
            var payload = {};
            formData.forEach(function (val, key) {
                // Skip masked placeholder values
                if (val === '***') return;
                payload[key] = val;
            });

            btnLoading(btnSave, 'Saving...');
            try {
                var data = await api.post('/api/settings', payload);
                toast(data.message || 'Settings saved.', data.success ? 'success' : 'danger');
                // Do NOT reload from API — it returns masked "***" for keys.
                // Form values stay as-is since save succeeded.
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnSave);
            }
        });
    }

    // ==================================================================
    // 3b. Per-section Save buttons
    // ==================================================================
    document.querySelectorAll('.btn-section-save').forEach(function (btn) {
        btn.addEventListener('click', async function () {
            var section = btn.dataset.section;
            var card = btn.closest('.card');
            if (!card) return;
            var fields = card.querySelectorAll('[name]');
            var payload = {};
            fields.forEach(function (el) {
                if (el.value && el.value !== '***') {
                    payload[el.getAttribute('name')] = el.value;
                }
            });
            btnLoading(btn, 'Saving...');
            try {
                var data = await api.post('/api/settings', payload);
                toast(data.message || 'Saved.', data.success ? 'success' : 'danger');
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btn);
            }
        });
    });

    // ==================================================================
    // 4. Restore Defaults
    // ==================================================================
    if (btnReset) {
        btnReset.addEventListener('click', async function () {
            if (!confirm('Reset all settings to defaults? This cannot be undone.')) return;
            btnLoading(btnReset, 'Resetting...');
            try {
                var data = await api.post('/api/settings/reset');
                toast(data.message || 'Settings reset.', data.success ? 'success' : 'info');
                if (data.success) {
                    await loadSettings();
                }
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnReset);
            }
        });
    }

    // ==================================================================
    // 5. Hotkey Controls
    // ==================================================================
    var btnRecord = document.getElementById('btn-record-shortcut');
    var btnEnable = document.getElementById('btn-enable-hotkey');
    var btnDisable = document.getElementById('btn-disable-hotkey');
    var hotkeyDisplay = document.getElementById('hotkey-display');
    var hotkeyStatusText = document.getElementById('hotkey-status-text');

    var isRecording = false;
    var recordedKeys = [];

    // Load hotkey info on page open
    loadHotkeyInfo();

    async function loadHotkeyInfo() {
        try {
            var data = await api.get('/api/hotkey/status');
            if (data.success && data.hotkey) {
                if (hotkeyDisplay) hotkeyDisplay.value = data.hotkey.shortcut || 'ctrl+shift+a';
                if (hotkeyStatusText) {
                    hotkeyStatusText.textContent = 'Status: ' +
                        (data.hotkey.registered ? 'Active (' + data.hotkey.shortcut + ')' : 'Not registered');
                }
            }
        } catch (err) {
            console.warn('Failed to load hotkey info:', err);
        }
    }

    // Record shortcut
    if (btnRecord) {
        btnRecord.addEventListener('click', function () {
            if (isRecording) {
                // Stop recording
                stopRecording();
                return;
            }
            // Start recording
            isRecording = true;
            recordedKeys = [];
            btnRecord.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Listening... Press keys...';
            btnRecord.classList.remove('btn-outline-warning');
            btnRecord.classList.add('btn-warning');
        });
    }

    // Capture keydown during recording
    document.addEventListener('keydown', function (e) {
        if (!isRecording) return;
        e.preventDefault();
        e.stopPropagation();

        var parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        if (e.metaKey) parts.push('win');

        // Ignore standalone modifier key presses
        var nonModifiers = ['Control', 'Shift', 'Alt', 'Meta'];
        if (nonModifiers.indexOf(e.key) === -1) {
            var key = e.key.toLowerCase();
            if (key === ' ') key = 'space';
            parts.push(key);

            var shortcut = parts.join('+');
            finishRecording(shortcut);
        }
    });

    async function finishRecording(shortcut) {
        stopRecording();
        if (hotkeyDisplay) hotkeyDisplay.value = shortcut;

        try {
            var data = await api.post('/api/hotkey/change', { shortcut: shortcut });
            if (data.success) {
                toast('Shortcut changed to ' + shortcut, 'success');
                await loadHotkeyInfo();
            } else {
                toast(data.message, 'danger');
            }
        } catch (err) {
            toast(err.message, 'danger');
        }
    }

    function stopRecording() {
        isRecording = false;
        recordedKeys = [];
        if (btnRecord) {
            btnRecord.innerHTML = '<i class="bi bi-record-circle me-1"></i> Record Shortcut';
            btnRecord.classList.remove('btn-warning');
            btnRecord.classList.add('btn-outline-warning');
        }
    }

    // Enable / Disable
    if (btnEnable) {
        btnEnable.addEventListener('click', async function () {
            btnLoading(btnEnable, 'Enabling...');
            try {
                var data = await api.post('/api/hotkey/start');
                toast(data.message, data.success ? 'success' : 'warning');
                await loadHotkeyInfo();
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnEnable);
            }
        });
    }

    if (btnDisable) {
        btnDisable.addEventListener('click', async function () {
            btnLoading(btnDisable, 'Disabling...');
            try {
                var data = await api.post('/api/hotkey/stop');
                toast(data.message, data.success ? 'success' : 'info');
                await loadHotkeyInfo();
            } catch (err) {
                toast(err.message, 'danger');
            } finally {
                btnRestore(btnDisable);
            }
        });
    }
})();
