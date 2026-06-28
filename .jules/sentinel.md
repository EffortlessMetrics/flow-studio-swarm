
## 2025-06-28 - Replace xml.etree with defusedxml to prevent XXE
**Vulnerability:** The python xml.etree module was being used to parse XML files, which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The built-in xml.etree.ElementTree in Python does not protect against maliciously constructed XML data.
**Prevention:** Use the `defusedxml` package instead which provides a secure drop-in replacement for the standard library module.
