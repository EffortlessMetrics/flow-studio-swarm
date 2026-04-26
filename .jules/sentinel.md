## 2024-05-15 - Replace Standard XML Parser with defusedxml
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially external XML files in `swarm/runtime/test_parser.py`.
**Learning:** The built-in XML parsing modules in Python are vulnerable to XML External Entity (XXE) processing, which can lead to information disclosure or denial of service.
**Prevention:** Always use `defusedxml` packages instead of standard library XML parsing tools across the codebase.
