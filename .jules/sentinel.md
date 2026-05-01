
## 2025-02-14 - Fix XXE vulnerability in test output parsing
**Vulnerability:** XML External Entity (XXE) vulnerability in `swarm/runtime/test_parser.py` via `xml.etree.ElementTree`.
**Learning:** Using the built-in `xml.etree` module for parsing arbitrary XML input exposes applications to XXE vulnerabilities. Even for parsing test output, we must be defensive against malicious output or artifacts.
**Prevention:** Always use `defusedxml` to parse XML data when the input source isn't fully trusted, and add a `# SECURITY: ...` comment.
