
from swarm.runtime.test_parser import parse_test_output


def test_parse_junit_xml(tmp_path):
    xml_path = tmp_path / "test.xml"
    xml_path.write_text("""<?xml version="1.0" ?>
<testsuites>
  <testsuite errors="0" failures="1" name="tests" skipped="0" tests="1" time="0.0">
    <testcase classname="test_foo" name="test_bar" time="0.0">
      <failure message="Error">Failed</failure>
    </testcase>
  </testsuite>
</testsuites>
""")
    summary = parse_test_output(xml_path, format_hint="junit")
    assert summary.total == 1
    assert summary.failed == 1

def test_parse_playwright_zip(tmp_path):
    # Just checking it handles bad input for now.
    bad_zip = tmp_path / "test.zip"
    bad_zip.write_bytes(b"not a zip")
    summary = parse_test_output(bad_zip, format_hint="playwright")
    assert summary.total == 0
