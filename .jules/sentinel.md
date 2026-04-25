## 2026-04-25 - Prevent XXE in XML Test Parsing
**Vulnerability:** Found standard xml.etree.ElementTree used to parse XML test outputs, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Python's built-in xml.etree is vulnerable by default. Even for internal tools, parsing external test outputs can be dangerous if the XML source is malicious or untrusted.
**Prevention:** Use defusedxml.ElementTree for parsing all XML documents, as it is protected against XML-based attacks.
