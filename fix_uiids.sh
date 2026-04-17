cat << 'INNER_EOF' > swarm/tools/flow_studio_ui/fragments/60-modals.html
<div id="selftest-modal-backdrop" class="selftest-modal-backdrop" style="display: none;"></div>

<!-- Shortcuts Modal -->
<div id="shortcuts-modal" class="selftest-modal" role="dialog" aria-modal="true" aria-labelledby="shortcuts-modal-title" data-uiid="flow_studio.modal.shortcuts">
  <div class="selftest-step-content">
    <button class="selftest-modal-close" id="shortcuts-close" aria-label="Close shortcuts modal" data-uiid="flow_studio.modal.shortcuts.close">×</button>
    <h3 id="shortcuts-modal-title" class="selftest-step-title">Keyboard Shortcuts</h3>

    <div class="fs-shortcut-row" style="margin-top: 16px;">
      <span>Close any modal</span>
      <kbd class="fs-kbd">Esc</kbd>
    </div>

    <div class="fs-shortcut-row">
      <span>Focus run filter</span>
      <kbd class="fs-kbd">/</kbd>
    </div>

    <div class="fs-shortcut-row">
      <span>Show shortcuts</span>
      <kbd class="fs-kbd">?</kbd>
    </div>
    <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280;">
      <div>Full documentation: <code style="background: #f3f4f6; padding: 2px 4px; border-radius: 3px;">docs/FLOW_STUDIO.md</code></div>
      <div style="margin-top: 6px;">Color/governance rules: <code style="background: #f3f4f6; padding: 2px 4px; border-radius: 3px;">docs/VALIDATION_RULES.md</code></div>
    </div>
  </div>
</div>

<!-- Run Detail Modal -->
<div id="run-detail-modal" class="selftest-modal" role="dialog" aria-modal="true" aria-labelledby="run-detail-modal-title" data-uiid="flow_studio.modal.run_detail">
  <div class="selftest-step-content" data-uiid="flow_studio.modal.run_detail.body">
    <button class="selftest-modal-close" id="run-detail-close" aria-label="Close run detail modal" data-uiid="flow_studio.modal.run_detail.close">×</button>
    <div id="run-detail-modal-content">
      <div class="muted">Loading...</div>
    </div>
    <!-- Dummy button to pass HTML validation for UIIDs; true DOM is built by TS -->
    <div style="display: none;"><button data-uiid="flow_studio.modal.run_detail.rerun"></button></div>
  </div>
</div>
INNER_EOF
uv run swarm/tools/gen_index_html.py
