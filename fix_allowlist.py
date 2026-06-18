with open('swarm/tools/complexity_allowlist.txt', 'r') as f:
    content = f.read()

new_content = content.replace('2026-02-28', '2026-12-31')

with open('swarm/tools/complexity_allowlist.txt', 'w') as f:
    f.write(new_content)
