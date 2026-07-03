
## 2024-07-04 - Fix XXE in JUnit XML Parser
**Vulnerability:** Found XML External Entity (XXE) vulnerability in test parser using standard xml.etree.ElementTree.
**Learning:** The Python standard library XML parser is vulnerable to XXE out of the box when parsing XML files.
**Prevention:** Always use defusedxml instead of the standard xml library when parsing untrusted XML files like test results.
