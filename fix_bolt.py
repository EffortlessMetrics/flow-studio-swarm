with open(".jules/bolt.md", "r") as f:
    content = f.read()
content = content.replace("returned.##", "returned.\n\n##")
with open(".jules/bolt.md", "w") as f:
    f.write(content)
