from pathlib import Path

from swarm.runtime.test_parser import parse_junit_xml


def test_parse_junit_xml(tmp_path: Path):
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite errors="0" failures="1" name="pytest" skipped="0" tests="1" time="0.0">
    <testcase classname="test_foo" name="test_bar" time="0.0">
      <failure message="test failed">traceback</failure>
    </testcase>
  </testsuite>
</testsuites>""")
    summary = parse_junit_xml(xml_file)
    assert summary.total == 1
    assert summary.failed == 1
