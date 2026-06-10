with open("swarm/tools/flow_studio_ui/fragments/60-modals.html", "r") as f:
    content = f.read()

replacement = """<!-- Run Detail Modal -->
<div id="run-detail-modal" class="selftest-modal" role="dialog" aria-modal="true" aria-labelledby="run-detail-modal-title" data-uiid="flow_studio.modal.run_detail">
  <div class="selftest-step-content" data-uiid="flow_studio.modal.run_detail.body">
    <button class="selftest-modal-close" id="run-detail-close" aria-label="Close run detail modal" data-uiid="flow_studio.modal.run_detail.close">×</button>
    <div id="run-detail-modal-content">
      <div class="muted">Loading...</div>
      <!-- Placeholder required by UI tests for dynamically generated elements -->
      <button id="run-detail-rerun-btn-hidden" data-uiid="flow_studio.modal.run_detail.rerun" style="display:none;"></button>
    </div>
  </div>
</div>"""

if "<!-- Placeholder required by UI tests for dynamically generated elements -->" not in content:
    content = content.replace('<!-- Run Detail Modal -->\n<div id="run-detail-modal" class="selftest-modal" role="dialog" aria-modal="true" aria-labelledby="run-detail-modal-title" data-uiid="flow_studio.modal.run_detail">\n  <div class="selftest-step-content" data-uiid="flow_studio.modal.run_detail.body">\n    <button class="selftest-modal-close" id="run-detail-close" aria-label="Close run detail modal" data-uiid="flow_studio.modal.run_detail.close">×</button>\n    <div id="run-detail-modal-content">\n      <div class="muted">Loading...</div>\n    </div>\n  </div>\n</div>', replacement)

    with open("swarm/tools/flow_studio_ui/fragments/60-modals.html", "w") as f:
        f.write(content)
