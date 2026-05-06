import re
f = open('update_dashboard.py', 'r')
lines = f.readlines()
f.close()
result = []
for line in lines:
      stripped = line.rstrip('\n')
      if stripped == '':
                result.append('')
                continue
            content_part = stripped.lstrip()
    if content_part == '':
              result.append('')
              continue
          spaces_count = len(stripped) - len(content_part)
    if spaces_count > 0 and spaces_count % 4 != 0:
              spaces_count = (spaces_count // 4) * 4
          result.append(' ' * spaces_count + content_part)
g = open('update_dashboard.py', 'w')
g.write('\n'.join(result) + '\n')
g.close()
print('Indentation normalized')
