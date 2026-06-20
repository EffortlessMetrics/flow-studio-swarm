
## 2026-06-20 - Prevent XXE Vulnerabilities
**Vulnerability:** The standard library `xml.etree.ElementTree` is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing untrusted XML files.
**Learning:** The test parser processed potentially malicious XML test output from unknown test frameworks without proper safeguards against XXE.
**Prevention:** Always use `defusedxml.ElementTree` instead of the standard library's XML parsing modules when dealing with untrusted XML input to protect against these vulnerabilities by default.
