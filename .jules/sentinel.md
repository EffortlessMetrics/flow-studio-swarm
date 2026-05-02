
## 2026-05-02 - XXE Prevention with defusedxml
**Vulnerability:** Standard xml.etree.ElementTree is susceptible to XML External Entity (XXE) injection.
**Learning:** Untrusted XML should never be parsed with the default Python standard library module without defusing.
**Prevention:** Always use defusedxml.ElementTree as a drop-in replacement for safe XML parsing.
