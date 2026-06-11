
## 2025-02-24 - Replace xml.etree.ElementTree with defusedxml to prevent XXE
**Vulnerability:** The standard library `xml.etree.ElementTree` is used to parse JUnit XML files in `swarm/runtime/test_parser.py`, which is vulnerable to XML External Entity (XXE) injection and Billion Laughs attacks.
**Learning:** Even internal developer tools parsing test outputs need XXE protection, as test results can be manipulated by malicious tests to exfiltrate files or cause Denial of Service (DoS) during log parsing. The memory explicitely states: "When parsing XML files within the project, strictly use `defusedxml.ElementTree` instead of the standard library's `xml.etree.ElementTree` to prevent XML External Entity (XXE) and billion laughs vulnerabilities."
**Prevention:** Always use `defusedxml` whenever parsing XML files, even in testing or parsing utilities, rather than the standard library's `xml`.
