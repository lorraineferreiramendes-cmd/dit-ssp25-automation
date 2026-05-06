import re
with open('update_dashboard.py', 'r') as f:
      content = f.read()
  fixed = re.sub(r'[ \t]{2,}r = requests\.get\(', '    r = requests.get(', content)
with open('update_dashboard.py', 'w') as f:
      f.write(fixed)
  print('Indentation fixed')
