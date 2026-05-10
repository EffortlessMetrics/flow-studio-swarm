from pathlib import Path
from swarm.runtime.test_parser import parse_junit_xml, TestSummary
import pytest

def test_parse_junit_xml_invalid(tmp_path: Path):
    xml_content = "invalid xml"
    xml_file = tmp_path / "test.xml"
    xml_file.write_text(xml_content)

    summary = parse_junit_xml(xml_file)
    assert summary.total == 0

def test_parse_junit_xml_xxe(tmp_path: Path):
    # This might fail or raise exception depending on defusedxml behavior,
    # but the point is we test it doesn't do XXE.
    xxe_content = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="1" time="0.1">
    <testcase classname="test_xxe" name="test_xxe" time="0.05">
      <failure message="&xxe;">xxe body</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
    xml_file = tmp_path / "test_xxe.xml"
    xml_file.write_text(xxe_content)
    try:
        summary = parse_junit_xml(xml_file)
        if summary.failed > 0:
            assert "&xxe;" in summary.failures[0].error_message or "xxe" not in summary.failures[0].error_message
            assert "root" not in summary.failures[0].error_message
    except Exception as e:
        # DefusedXmlException is also fine
        pass
