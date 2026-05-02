
## 2024-05-02 - Mitigated XML External Entity (XXE) in Test Parser
**Vulnerability:** Found usage of standard `xml.etree.ElementTree` for parsing JUnit XML which is susceptible to XXE attacks.
**Learning:** Python's standard XML parsers are vulnerable to XML injection.
**Prevention:** Always use `defusedxml` when parsing untrusted XML data to prevent XXE.
