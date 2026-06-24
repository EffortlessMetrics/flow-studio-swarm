
## 2024-05-24 - XML External Entity (XXE) Vulnerability
**Vulnerability:** The codebase was using the standard library's `xml.etree.ElementTree` which is vulnerable to XXE and billion laughs attacks when parsing untrusted XML.
**Learning:** The project uses pytest output formats which include JUnit XML. Parsing these with the standard library exposes the agent to XML attacks. `defusedxml` should be used for safe XML parsing.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML files.
