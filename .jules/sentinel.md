## 2026-05-08 - Fixed XXE Vulnerability in XML Test Output Parser
**Vulnerability:** The application used standard `xml.etree.ElementTree` to parse JUnit XML files from potentially untrusted test outputs, risking XML External Entity (XXE) attacks.
**Learning:** Parsing third-party or user-provided XML files (like JUnit results) with standard libraries is unsafe without disabling external entities. Test environments can be compromised.
**Prevention:** Always use `defusedxml` as a drop-in replacement when parsing any XML files that aren't strictly generated and controlled internally by the application.
