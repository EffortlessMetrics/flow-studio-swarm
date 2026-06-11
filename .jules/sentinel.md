
## 2025-03-05 - Fix XXE in Test Parser
**Vulnerability:** XML External Entity (XXE) and billion laughs vulnerabilities via standard library `xml.etree.ElementTree` in JUnit XML parser.
**Learning:** Python's standard `xml.etree.ElementTree` is vulnerable to XXE by default. It was used in `parse_junit_xml` which parses untrusted test output files.
**Prevention:** Always use `defusedxml.ElementTree` when parsing XML from external or untrusted sources (like test reports from arbitrary runner output) within the project.
