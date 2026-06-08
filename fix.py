import re
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()
new_config = open('config_new.js', 'r', encoding='utf-8').read()
new_content = re.sub(r'const CONFIG = \{.*?\};', new_config, content, flags=re.DOTALL)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("✅ Listo")
