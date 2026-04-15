import re

with open('app.py', 'r') as f:
    text = f.read()

def replacer(match):
    full_match = match.group(0)
    # Extract the chart function name inside charts.CHART_NAME(...)
    chart_name_match = re.search(r'charts\.([a-zA-Z0-9_]+)\(', full_match)
    if chart_name_match:
        chart_name = chart_name_match.group(1)
        # If a key= is not already present, we append it
        if "key=" not in full_match:
            full_match = full_match.replace("use_container_width=True", f"use_container_width=True, key='{chart_name}'")
    return full_match

new_text = re.sub(r'st\.plotly_chart\([^)]+\)', replacer, text)

with open('app.py', 'w') as f:
    f.write(new_text)

print("Keys patched!")
