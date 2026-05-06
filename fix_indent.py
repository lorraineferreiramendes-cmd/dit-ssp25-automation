import re
import sys
f = open('update_dashboard.py', 'r')
content = f.read()
f.close()
spaces4 = chr(32) * 4
pattern = r'[ \t]{2,}r = requests\.get\('
replacement = spaces4 + 'r = requests.get('
fixed = re.sub(pattern, replacement, content)
g = open('update_dashboard.py', 'w')
g.write(fixed)
g.close()
print('Done')
