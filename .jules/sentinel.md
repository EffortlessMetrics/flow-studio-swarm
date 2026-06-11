## 2025-02-27 - [CRITICAL] Fix XXE vulnerability in XML parsing
**Vulnerability:** Use of standard `xml.etree.ElementTree` parsing without protection against XML External Entity (XXE) attacks in test parser.
**Learning:** `xml.etree.ElementTree` is vulnerable to XXE out of the box, standard Python library doesn't securely parse un-trusted XML.
**Prevention:** Always use `defusedxml` library for XML parsing across the repository to mitigate XXE injection risks.
