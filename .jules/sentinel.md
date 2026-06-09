
## 2025-06-09 - XXE Vulnerability in XML Parser
**Vulnerability:** The codebase was using the standard library `xml.etree.ElementTree` to parse external XML files (JUnit test output), which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Using standard `xml.etree.ElementTree` for untrusted input is inherently unsafe in Python. `defusedxml` must be used instead to mitigate these attacks.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing any XML files in the repository.
