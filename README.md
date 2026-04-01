# stash

## structure

```
stash/
├── index.html          — never touch
├── builder.py          — run this
├── bookmarks.json      — auto-generated, then you fill in url + category
├── stash.json          — auto-generated
└── screenshots/
    ├── 2026/
    └── 2025/
```

## setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pillow pillow-heif
```

## adding bookmarks

```bash
# 1. drop screenshot into screenshots/2026/image.png

# 2. run builder — scans screenshots, adds new entries to bookmarks.json
source venv/bin/activate
python3 builder.py

# 3. open bookmarks.json, fill in url and category for new entries
# 4. run builder again — generates stash.json
python3 builder.py
deactivate

# 5. preview
python3 -m http.server 8000
```

## deploy

```bash
git add .
git commit -m "add bookmarks"
git push
```
