## 2026-05-09 - [XML External Entity (XXE) Vulnerability]
**Vulnerability:** [Usage of standard `xml.etree.ElementTree` parsing without protection against XXE attacks]
**Learning:** [Standard XML parsing libraries are vulnerable to XXE by default. In `swarm/runtime/test_parser.py`, parsing untrusted JUnit XML test results with `ET.parse()` could expose the system to XXE.]
**Prevention:** [Always use secure alternatives like `defusedxml` when parsing XML to prevent external entity injection.]
