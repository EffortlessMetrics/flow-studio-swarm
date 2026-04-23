## 2024-05-24 - XXE Vulnerability in XML Parser
**Vulnerability:** The test results parser (swarm/runtime/test_parser.py) used the standard xml.etree.ElementTree to parse JUnit XML, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Even internal tooling or test parsers can be a vector for XXE if they parse untrusted or externally generated XML files without safe parsers.
**Prevention:** Always use defusedxml instead of the standard library xml modules when parsing any XML data.
