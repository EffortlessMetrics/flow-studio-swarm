## 2024-06-23 - Fix XXE Vulnerability
**Vulnerability:** Used xml.etree.ElementTree which is vulnerable to XXE attacks.
**Learning:** The standard XML library is unsafe for untrusted data.
**Prevention:** Always use defusedxml.ElementTree instead.
