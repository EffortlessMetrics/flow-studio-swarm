
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
                            p = self.runs_dir / entry.name
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
                            p = self.examples_dir / entry.name
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
