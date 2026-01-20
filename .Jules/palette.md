## 2024-03-21 - [Generated Index File]
**Learning:** `swarm/tools/flow_studio_ui/index.html` is a generated build artifact. Committing it alongside source changes in `fragments/` creates noise and can lead to merge conflicts or accidental inclusion of unrelated changes.
**Action:** When working on Flow Studio UI, modify only the files in `fragments/` and `css/`. Run `make gen-index-html` to verify locally, but revert changes to `index.html` before committing unless explicitly instructed to update the build artifact.
