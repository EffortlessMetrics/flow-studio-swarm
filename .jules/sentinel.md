## 2026-05-10 - Fix XXE in JUnit XML Parser
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse JUnit XML files without disabling external entity resolution, which could lead to XXE attacks.
**Learning:** Standard library `xml.etree.ElementTree` is vulnerable to XXE by default. In test parsers dealing with externally provided XML files, this is a significant risk.
**Prevention:** Always use `defusedxml.ElementTree` as a drop-in replacement when parsing XML from untrusted or external sources.
