
## 2024-05-03 - XML External Entity (XXE) in Test Parser
**Vulnerability:** Found insecure usage of standard `xml.etree.ElementTree` parsing XML test reports in `test_parser.py`.
**Learning:** Built-in Python XML libraries are vulnerable to XXE by default and should never be used on untrusted data.
**Prevention:** Always use `defusedxml` package as a secure drop-in replacement for standard XML parsing libraries across the entire codebase.
