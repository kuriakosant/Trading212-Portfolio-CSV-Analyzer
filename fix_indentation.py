import re

with open("charts.py", "r") as f:
    text = f.read()

# Fix unindented 'if' statements right after 'sym = ...'
text = re.sub(r'(\n    sym = "€" if base_currency == "EUR" else "\$"\n)if ', r'\1    if ', text)

with open("charts.py", "w") as f:
    f.write(text)
