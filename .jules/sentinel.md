
## 2026-06-14 - Fix XXE vulnerability in XML parser
**Vulnerability:** Use of insecure standard library `xml.etree.ElementTree` parsing untrusted JUnit XML output could allow XML External Entity (XXE) injection and Billion Laughs attacks.
**Learning:** Python's standard `xml` libraries are vulnerable to malicious XML payloads by default. Test reports are often parsed indiscriminately.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing XML files to prevent XXE and related vulnerabilities.
