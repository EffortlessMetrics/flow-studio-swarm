## 2024-05-09 - Initial Creation
**Vulnerability:** Missing sentinel journal.
**Learning:** The Sentinel journal tracks critical security learnings.
**Prevention:** Created the file to start logging learnings.
## 2026-05-09 - Fix XML External Entity (XXE) vulnerability in test parser
**Vulnerability:** Untrusted XML parsing via standard library xml.etree.ElementTree.
**Learning:** The default Python XML parser is vulnerable to XML External Entity (XXE) attacks.
**Prevention:** Use defusedxml for all XML parsing.
