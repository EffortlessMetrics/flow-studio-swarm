
## 2026-06-15 - Fix XML parser XXE vulnerability
**Vulnerability:** Used insecure standard library `xml.etree.ElementTree` which is vulnerable to XXE (XML External Entity) and billion laughs attacks.
**Learning:** The built-in XML library is unsafe for parsing potentially malicious XML files. Even if test results are internal, it's safer to always use a safe XML parser.
**Prevention:** Always use `defusedxml` when parsing XML files in python projects.
