## 2026-05-06 - Mitigating XXE in Test Parser
**Vulnerability:** Insecure XML parsing using standard `xml.etree.ElementTree` in `test_parser.py`.
**Learning:** Python's standard `xml.etree` is vulnerable to XML External Entity (XXE) attacks by default, which can lead to file disclosure or DoS.
**Prevention:** Always use `defusedxml` as a secure drop-in replacement when parsing untrusted XML data.
