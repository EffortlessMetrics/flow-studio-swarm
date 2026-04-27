## 2024-05-24 - Fix XXE in Test Output Parsing
**Vulnerability:** Found standard `xml.etree.ElementTree` usage without protections when parsing JUnit XML files.
**Learning:** Test artifacts are often parsed from untrusted execution environments and can be vectors for XXE attacks if the parser is vulnerable.
**Prevention:** Use `defusedxml` instead of the standard library XML modules when parsing untrusted XML data.
