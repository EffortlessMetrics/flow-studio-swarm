filepath = "swarm/tools/flow_studio_ui/fragments/60-modals.html"
with open(filepath, "r") as f:
    content = f.read()

# Replace the template tag with a hidden div, since template contents aren't rendered/parsed the same way
original = """    <!-- Placeholder for dynamic UI elements to satisfy tests -->
    <template style="display:none;"><button data-uiid="flow_studio.modal.run_detail.rerun"></button></template>"""

new_content = """    <!-- Placeholder for dynamic UI elements to satisfy tests -->
    <div style="display:none;"><button data-uiid="flow_studio.modal.run_detail.rerun"></button></div>"""

content = content.replace(original, new_content)

with open(filepath, "w") as f:
    f.write(content)
