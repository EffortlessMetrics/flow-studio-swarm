
## 2024-05-04 - Mitigate XXE vulnerability in XML parsing
**Vulnerability:** Found standard `xml.etree.ElementTree` being used to parse XML data, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Python's standard `xml.etree` is not secure against maliciously constructed XML data. Standard library components are not always inherently secure.
**Prevention:** Always use `defusedxml` as a drop-in replacement for any XML parsing tasks that might handle untrusted input.

## 2024-05-04 - Fix CI check failures
**Vulnerability:** Not a security vulnerability but rather fragile test cases.
**Learning:**
- Mocking tests that use loops checking multiple conditions (like `_resolve_base_ref` falling back over candidate branches) requires enough side effects to exhaust all attempts.
- UI elements parsed from JS strings shouldn't be statically verified by a tool ignoring script tags.
**Prevention:** Avoid static testing of dynamic code features and trace code properly when modifying test assertions.
