import json
import re
from pathlib import Path
from fastapi import HTTPException

WORDS = json.loads(Path(__file__).with_name('profanity.json').read_text())
LINK = re.compile(r'https?://|www\.|\b[\w-]+\.[a-z]{2,}(?:[/\s]|$)', re.I)

def moderate(name, text):
    content = name + ' ' + text
    if any(re.search(r'\b' + re.escape(word) + r'\b', content, re.I) for word in WORDS):
        raise HTTPException(422, 'Please keep your message respectful.')
    return 'pending' if LINK.search(content) else 'approved'
