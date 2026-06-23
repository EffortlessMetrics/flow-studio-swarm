
## 2024-05-24 - XML External Entity (XXE) Vulnerability Prevention
**Vulnerability:** The native `xml.etree.ElementTree` is vulnerable to XML external entity (XXE) and billion laughs attacks when parsing untrusted XML data.
**Learning:** The built-in Python XML parser does not protect against malicious XML payloads, leaving applications exposed when parsing files like JUnit test results.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` as a drop-in replacement when parsing XML files in this repository.
