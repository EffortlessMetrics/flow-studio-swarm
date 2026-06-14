
## 2025-03-01 - XXE Vulnerability in Test Parser
**Vulnerability:** Used standard library `xml.etree.ElementTree` to parse external XML test results, exposing the system to XML External Entity (XXE) and billion laughs attacks.
**Learning:** External test output files must be treated as untrusted input. The standard library XML parser does not protect against malicious XML documents.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing any XML files, including internal tooling like test results.
