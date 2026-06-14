
# 1. swarm/flowstudio/config.py
with open("swarm/flowstudio/config.py", "r") as f:
    content = f.read()

old_runs = """    def list_runs(self) -> list[Path]:
        \"\"\"List all active runs.\"\"\"
        if not self.runs_dir.exists():
            return []
        return sorted(
            p for p in self.runs_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        )"""

new_runs = """    def list_runs(self) -> list[Path]:
        \"\"\"List all active runs.\"\"\"
        if not self.runs_dir.exists():
            return []
        import os
        runs = []
        try:
            with os.scandir(self.runs_dir) as entries:
                for e in entries:
                    if e.is_dir() and not e.name.startswith("."):
                        runs.append(Path(e.path))
        except OSError:
            pass
        return sorted(runs)"""

old_examples = """    def list_examples(self) -> list[Path]:
        \"\"\"List all example runs.\"\"\"
        if not self.examples_dir.exists():
            return []
        return sorted(
            p for p in self.examples_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        )"""

new_examples = """    def list_examples(self) -> list[Path]:
        \"\"\"List all example runs.\"\"\"
        if not self.examples_dir.exists():
            return []
        import os
        examples = []
        try:
            with os.scandir(self.examples_dir) as entries:
                for e in entries:
                    if e.is_dir() and not e.name.startswith("."):
                        examples.append(Path(e.path))
        except OSError:
            pass
        return sorted(examples)"""

content = content.replace(old_runs, new_runs)
content = content.replace(old_examples, new_examples)

with open("swarm/flowstudio/config.py", "w") as f:
    f.write(content)

# 2. swarm/api/services/spec_manager.py
with open("swarm/api/services/spec_manager.py", "r") as f:
    content = f.read()

old_runs_spec = """        for run_dir in sorted(self.runs_root.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue

            state_file = run_dir / "run_state.json"
            if state_file.exists():
                try:
                    state = json.loads(state_file.read_text(encoding="utf-8"))
                    runs.append(
                        {
                            "run_id": state.get("run_id", run_dir.name),
                            "flow_key": state.get("flow_key"),
                            "status": state.get("status"),
                            "timestamp": state.get("timestamp"),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load run state %s: %s", run_dir, e)

            if len(runs) >= limit:
                break"""

new_runs_spec = """        import os
        try:
            with os.scandir(self.runs_root) as entries:
                # Sort entries by name directly to avoid creating Path objects unnecessarily
                sorted_entries = sorted(
                    [e for e in entries if e.is_dir()],
                    key=lambda e: e.name,
                    reverse=True
                )

                for entry in sorted_entries:
                    state_file_path = os.path.join(entry.path, "run_state.json")
                    if os.path.exists(state_file_path):
                        try:
                            with open(state_file_path, "r", encoding="utf-8") as sf:
                                state = json.load(sf)
                            runs.append(
                                {
                                    "run_id": state.get("run_id", entry.name),
                                    "flow_key": state.get("flow_key"),
                                    "status": state.get("status"),
                                    "timestamp": state.get("timestamp"),
                                }
                            )
                        except Exception as e:
                            logger.warning("Failed to load run state %s: %s", entry.path, e)

                    if len(runs) >= limit:
                        break
        except OSError:
            pass"""

content = content.replace(old_runs_spec, new_runs_spec)
with open("swarm/api/services/spec_manager.py", "w") as f:
    f.write(content)


# 3. swarm/runtime/evolution.py
with open("swarm/runtime/evolution.py", "r") as f:
    content = f.read()

old_runs_evolve = """    run_dirs = sorted(runs_root.iterdir(), reverse=True)[:limit]

    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue"""

new_runs_evolve = """    import os
    run_entries = []
    try:
        with os.scandir(runs_root) as entries:
            # Get valid directories first
            run_entries = [e for e in entries if e.is_dir()]
    except OSError:
        pass

    # Sort by name descending and limit
    run_entries.sort(key=lambda e: e.name, reverse=True)
    run_entries = run_entries[:limit]

    for entry in run_entries:
        run_dir = Path(entry.path)"""

content = content.replace(old_runs_evolve, new_runs_evolve)
with open("swarm/runtime/evolution.py", "w") as f:
    f.write(content)

# 4. swarm/runtime/statsdb/rebuild.py
with open("swarm/runtime/statsdb/rebuild.py", "r") as f:
    content = f.read()

if "import os" not in content:
    content = "import os\n" + content

old_1 = """            run_ids = [
                d.name for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]"""

new_1 = """            run_ids = []
            try:
                with os.scandir(runs_dir) as entries:
                    run_ids = [
                        e.name for e in entries if e.is_dir() and not e.name.startswith(".")
                    ]
            except OSError:
                pass"""

old_2 = """        run_ids = [d.name for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]"""

new_2 = """        run_ids = []
        try:
            with os.scandir(runs_dir) as entries:
                run_ids = [e.name for e in entries if e.is_dir() and not e.name.startswith(".")]
        except OSError:
            pass"""

old_3 = """                for flow_dir in run_path.iterdir():
                    if not flow_dir.is_dir() or flow_dir.name.startswith("."):
                        continue"""

new_3 = """                flow_entries = []
                try:
                    with os.scandir(run_path) as entries:
                        flow_entries = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
                except OSError:
                    pass

                for entry in flow_entries:
                    flow_dir = Path(entry.path)"""

content = content.replace(old_1, new_1)
content = content.replace(old_2, new_2)
content = content.replace(old_3, new_3)

with open("swarm/runtime/statsdb/rebuild.py", "w") as f:
    f.write(content)

# 5. swarm/tools/run_inspector.py
with open("swarm/tools/run_inspector.py", "r") as f:
    content = f.read()

old_ri_runs = """        # Active runs (gitignored)
        if self.runs_dir.exists():
            for entry in self.runs_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    run_data = {
                        "run_id": entry.name,
                        "run_type": "active",
                        "path": str(entry),
                    }
                    # Load optional metadata
                    metadata = self._load_run_metadata(entry)
                    run_data.update(metadata)
                    runs.append(run_data)"""

new_ri_runs = """        # Active runs (gitignored)
        if self.runs_dir.exists():
            import os
            try:
                with os.scandir(self.runs_dir) as entries:
                    for entry in entries:
                        if entry.is_dir() and not entry.name.startswith("."):
                            p = Path(entry.path)
                            run_data = {
                                "run_id": entry.name,
                                "run_type": "active",
                                "path": str(p),
                            }
                            # Load optional metadata
                            metadata = self._load_run_metadata(p)
                            run_data.update(metadata)
                            runs.append(run_data)
            except OSError:
                pass"""

old_ri_examples = """        # Example runs (committed)
        if self.examples_dir.exists():
            for entry in self.examples_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    run_data = {
                        "run_id": entry.name,
                        "run_type": "example",
                        "path": str(entry),
                    }
                    # Load optional metadata
                    metadata = self._load_run_metadata(entry)
                    run_data.update(metadata)
                    runs.append(run_data)"""

new_ri_examples = """        # Example runs (committed)
        if self.examples_dir.exists():
            import os
            try:
                with os.scandir(self.examples_dir) as entries:
                    for entry in entries:
                        if entry.is_dir() and not entry.name.startswith("."):
                            p = Path(entry.path)
                            run_data = {
                                "run_id": entry.name,
                                "run_type": "example",
                                "path": str(p),
                            }
                            # Load optional metadata
                            metadata = self._load_run_metadata(p)
                            run_data.update(metadata)
                            runs.append(run_data)
            except OSError:
                pass"""

content = content.replace(old_ri_runs, new_ri_runs)
content = content.replace(old_ri_examples, new_ri_examples)

with open("swarm/tools/run_inspector.py", "w") as f:
    f.write(content)
