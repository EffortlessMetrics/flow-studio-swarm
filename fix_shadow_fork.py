with open("tests/test_shadow_fork.py", "r") as f:
    content = f.read()

import re
content = re.sub(
    r'mock_git\.side_effect = \[\n\s*\(True, "main", ""\),  # Get current branch\n\s*\(False, "", "fatal"\),  # Base branch preferred fails\n\s*\(False, "", "fatal"\),  # Base branch origin/preferred fails\n\s*\(False, "", "fatal"\),  # main fails\n\s*\(False, "", "fatal"\),  # origin/main fails\n\s*\(False, "", "fatal"\),  # master fails\n\s*\(False, "", "fatal"\),  # origin/master fails\n\s*\(False, "", "fatal"\),  # HEAD fails\n\s*\(True, "", ""\),  # Uncommitted changes check\n\s*\(False, "", "fatal"\),  # create checkout failure\n\s*\]',
    'mock_git.side_effect = [\n                (True, "main", ""),  # Get current branch\n                (False, "", "fatal"),  # Base branch preferred fails\n                (False, "", "fatal"),  # Base branch origin/preferred fails\n                (False, "", "fatal"),  # main fails\n                (False, "", "fatal"),  # origin/main fails\n                (False, "", "fatal"),  # master fails\n                (False, "", "fatal"),  # origin/master fails\n                (False, "", "fatal"),  # HEAD fails\n                (False, "", "fatal"),  # Try to run git rev-parse HEAD (maybe detached)\n                (True, "", ""),  # Uncommitted changes check\n                (False, "", "fatal"),  # create checkout failure\n            ]',
    content
)

with open("tests/test_shadow_fork.py", "w") as f:
    f.write(content)
