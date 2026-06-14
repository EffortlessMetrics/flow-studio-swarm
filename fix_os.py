
with open("swarm/runtime/statsdb/rebuild.py", "r") as f:
    content = f.read()

if "import os" not in content:
    content = "import os\n" + content

with open("swarm/runtime/statsdb/rebuild.py", "w") as f:
    f.write(content)
