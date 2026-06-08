
## 2026-06-08 - Prevent XXE Vulnerability with defusedxml
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` in `swarm/runtime/test_parser.py`.
**Learning:** The built-in `xml.etree.ElementTree` is vulnerable to XXE attacks when parsing untrusted XML data like test reports.
**Prevention:** Strictly use `defusedxml.ElementTree` instead of the standard library's XML parsers.
