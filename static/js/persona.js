/**
 * ScreenMate Persona — CRUD management page.
 */
(function () {
    'use strict';
    var api = window.ScreenMate.api;
    var toast = window.ScreenMate.toast;
    var btnLoading = window.ScreenMate.btnLoading;
    var btnRestore = window.ScreenMate.btnRestore;

    var listEl = document.getElementById('persona-list');
    var nameEl = document.getElementById('persona-name');
    var descEl = document.getElementById('persona-desc');
    var promptEl = document.getElementById('persona-prompt');
    var btnSave = document.getElementById('btn-save-persona');
    var btnClear = document.getElementById('btn-clear-persona');
    var btnRefresh = document.getElementById('btn-refresh-personas');

    var editingOriginalName = null;

    function loadList() {
        api.get('/api/personas').then(function (data) {
            if (!data.success || !data.personas) return;
            var items = data.personas;
            if (!items.length) {
                listEl.innerHTML = '<p class="text-secondary text-center py-3 mb-0">No personas yet.</p>';
                return;
            }
            listEl.innerHTML = items.map(function (p) {
                var badge = p.is_default ? ' <span class="badge bg-secondary">default</span>' : '';
                return (
                    '<div class="persona-card border-bottom border-secondary">' +
                    '  <div class="persona-header px-3 py-2 d-flex align-items-center gap-2" ' +
                    '       style="cursor:pointer;" onclick="var b=this.nextElementSibling;b.classList.toggle(\'d-none\')">' +
                    '    <i class="bi bi-chevron-right small text-secondary"></i>' +
                    '    <strong>' + ScreenMate.escapeHtml(p.name) + '</strong>' + badge +
                    '    <small class="text-secondary ms-auto">' + ScreenMate.escapeHtml(p.description || '') + '</small>' +
                    '  </div>' +
                    '  <div class="persona-body px-3 pb-2 d-none">' +
                    '    <p class="small text-secondary mb-1">' + ScreenMate.escapeHtml(p.description || 'No description') + '</p>' +
                    '    <pre class="small bg-dark text-light p-2 rounded" style="max-height:150px;overflow-y:auto;">' + ScreenMate.escapeHtml(p.system_prompt) + '</pre>' +
                    '    <div class="d-flex gap-2 mb-2">' +
                    '      <button class="btn btn-outline-info btn-sm btn-edit" data-name="' + ScreenMate.escapeHtml(p.name) + '">' +
                    '        <i class="bi bi-pencil me-1"></i>Edit</button>' +
                    (p.is_default ? '' :
                    '      <button class="btn btn-outline-danger btn-sm btn-delete" data-name="' + ScreenMate.escapeHtml(p.name) + '">' +
                    '        <i class="bi bi-trash me-1"></i>Delete</button>') +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                );
            }).join('');

            // Wire edit buttons
            listEl.querySelectorAll('.btn-edit').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var name = btn.dataset.name;
                    var found = items.find(function (p) { return p.name === name; });
                    if (found) {
                        editingOriginalName = name;
                        nameEl.value = found.name;
                        descEl.value = found.description || '';
                        promptEl.value = found.system_prompt || '';
                        nameEl.focus();
                    }
                });
            });
            // Wire delete buttons
            listEl.querySelectorAll('.btn-delete').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var name = btn.dataset.name;
                    if (!confirm('Delete persona "' + name + '"?')) return;
                    api.post('/api/personas/delete', { name: name }).then(function (r) {
                        toast(r.message, r.success ? 'success' : 'danger');
                        loadList();
                    });
                });
            });
        });
    }

    btnSave.addEventListener('click', function () {
        var name = nameEl.value.trim();
        if (!name) { toast('Name is required.', 'warning'); return; }
        var payload = {
            name: name,
            description: descEl.value.trim(),
            system_prompt: promptEl.value.trim(),
        };
        btnLoading(btnSave, 'Saving...');
        var promise;
        if (editingOriginalName && editingOriginalName !== name) {
            // Name changed: delete old, create new
            promise = api.post('/api/personas/delete', { name: editingOriginalName }).then(function () {
                return api.post('/api/personas/create', payload);
            });
        } else if (editingOriginalName) {
            promise = api.post('/api/personas/update', payload);
        } else {
            promise = api.post('/api/personas/create', payload);
        }
        promise.then(function (r) {
            toast(r.message, r.success ? 'success' : 'danger');
            if (r.success) { clearForm(); loadList(); }
        }).catch(function (e) { toast(e.message, 'danger'); })
        .finally(function () { btnRestore(btnSave); });
    });

    function clearForm() {
        nameEl.value = '';
        descEl.value = '';
        promptEl.value = '';
        editingOriginalName = null;
    }

    btnClear.addEventListener('click', clearForm);
    if (btnRefresh) btnRefresh.addEventListener('click', loadList);

    loadList();
})();
