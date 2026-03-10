## 2024-05-24 - API Routes Path Traversal via run_id
**Vulnerability:** Many FastAPI endpoint methods (such as those in `swarm/api/routes/runs_control.py`) did not properly validate the user-supplied `run_id` path parameter before utilizing it to locate the run's file artifacts on disk or via the state manager.
**Learning:** This exposes the application to path traversal attacks, allowing an attacker to inject characters like `..` to access files outside the intended runs root.
**Prevention:** Always sanitize and validate user-supplied path parameters (`run_id`, `flow_key`, `step_id`, etc.) using `swarm.runtime.safe_paths.validate_path_component` at the earliest point of entry in API endpoints before passing them to the service layer.
