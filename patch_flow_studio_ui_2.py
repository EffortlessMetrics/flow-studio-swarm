import re

with open('swarm/tools/flow_studio_ui/js/run_detail_modal.js', 'r') as f:
    content = f.read()

content = content.replace(
    '        <button id="run-detail-rerun-btn" class="fs-button-primary" style="flex: 1;">',
    '        <button id="run-detail-rerun-btn" data-uiid="flow_studio.modal.run_detail.rerun" class="fs-button-primary" style="flex: 1;">'
)

with open('swarm/tools/flow_studio_ui/js/run_detail_modal.js', 'w') as f:
    f.write(content)
