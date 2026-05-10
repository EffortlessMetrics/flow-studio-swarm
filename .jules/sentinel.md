
## 2026-05-10 - Prevent XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability in parsing test result XML files because standard `xml.etree.ElementTree` is used which does not protect against XXE attacks.
**Learning:** Even internal tooling like test parsers must use secure parsers because malicious XML inputs can lead to local file disclosures or denial of service attacks.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing untrusted XML.
