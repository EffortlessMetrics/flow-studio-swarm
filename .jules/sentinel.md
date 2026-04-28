## 2025-04-28 - Mitigate XXE vulnerability in JUnit XML parsing
**Vulnerability:** standard `xml.etree.ElementTree` is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Parsing external/untrusted XML like JUnit results without secure parsers can lead to local file disclosure or SSRF.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing untrusted XML.
