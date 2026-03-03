import swarm.tools.flow_studio_ui as ui
import re

html = ui.get_index_html()
lines = html.split('\n')
for i, l in enumerate(lines):
    if 'flow_studio.modal.run_detail.rerun' in l:
        print(f"Line {i+1}: {l}")
        print("Surrounding lines:")
        for j in range(max(0, i-5), min(len(lines), i+6)):
            print(f"{j+1}: {lines[j]}")
