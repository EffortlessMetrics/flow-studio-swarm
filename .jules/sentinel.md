
## 2024-05-04 - Mitigate XXE vulnerability in XML parsing
**Vulnerability:** Found standard `xml.etree.ElementTree` being used to parse XML data, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Python's standard `xml.etree` is not secure against maliciously constructed XML data. Standard library components are not always inherently secure.
**Prevention:** Always use `defusedxml` as a drop-in replacement for any XML parsing tasks that might handle untrusted input.
