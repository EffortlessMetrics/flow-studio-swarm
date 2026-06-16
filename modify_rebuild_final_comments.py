import os

filepath = "./swarm/runtime/statsdb/rebuild.py"
with open(filepath, "r") as f:
    content = f.read()

# Add comments for the first replacement
content = content.replace(
    '            with os.scandir(runs_dir) as entries:\n                run_ids = [\n                    d.name for d in entries if d.is_dir() and not d.name.startswith(".")\n                ]',
    '            # Performance optimization: Use os.scandir instead of Path.iterdir.\n            # DirEntry objects cache stat info, making is_dir() checks much faster\n            # when there are thousands of runs.\n            with os.scandir(runs_dir) as entries:\n                run_ids = [\n                    d.name for d in entries if d.is_dir() and not d.name.startswith(".")\n                ]'
)

# Add comments for the second replacement
content = content.replace(
    '        with os.scandir(runs_dir) as entries:\n            run_ids = [d.name for d in entries if d.is_dir() and not d.name.startswith(".")]',
    '        # Performance optimization: os.scandir avoids instantiating Path objects\n        # for every entry, reducing system stat calls during directory traversal.\n        with os.scandir(runs_dir) as entries:\n            run_ids = [d.name for d in entries if d.is_dir() and not d.name.startswith(".")]'
)

# Add comments for the third replacement
content = content.replace(
    '                with os.scandir(run_path) as flow_entries:\n                    for flow_dir in flow_entries:\n                        if not flow_dir.is_dir() or flow_dir.name.startswith("."):',
    '                # Performance optimization: Traversal of flow directories using os.scandir\n                # minimizes stat calls and significantly improves handoff processing speed.\n                with os.scandir(run_path) as flow_entries:\n                    for flow_dir in flow_entries:\n                        if not flow_dir.is_dir() or flow_dir.name.startswith("."):'
)

with open(filepath, "w") as f:
    f.write(content)
