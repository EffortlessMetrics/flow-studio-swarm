import re

with open('swarm/tools/flow_studio_ui/index.html', 'r') as f:
    content = f.read()

# Add data-uiid="flow_studio.modal.run_detail.rerun" to rerunBtn
content = content.replace(
    '        <button id="run-detail-rerun-btn" class="fs-button-primary" style="flex: 1;">',
    '        <button id="run-detail-rerun-btn" data-uiid="flow_studio.modal.run_detail.rerun" class="fs-button-primary" style="flex: 1;">'
)

with open('swarm/tools/flow_studio_ui/index.html', 'w') as f:
    f.write(content)

with open('swarm/tools/flow_studio_ui/src/run_detail_modal.ts', 'r') as f:
    content = f.read()

content = content.replace(
    '        <button id="run-detail-rerun-btn" class="fs-button-primary" style="flex: 1;">',
    '        <button id="run-detail-rerun-btn" data-uiid="flow_studio.modal.run_detail.rerun" class="fs-button-primary" style="flex: 1;">'
)

with open('swarm/tools/flow_studio_ui/src/run_detail_modal.ts', 'w') as f:
    f.write(content)
