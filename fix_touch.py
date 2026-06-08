with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "  document.addEventListener('keydown'"

new = """  let mouseDown = false, mousePanStartX = 0, mousePanStartY = 0;

  lbImg.addEventListener('mousedown', e => {
    if (scale > 1) { mouseDown = true; mousePanStartX = e.clientX; mousePanStartY = e.clientY; e.preventDefault(); }
  });
  document.addEventListener('mousemove', e => {
    if (!mouseDown || scale <= 1) return;
    panX = lastPanX + (e.clientX - mousePanStartX) / scale;
    panY = lastPanY + (e.clientY - mousePanStartY) / scale;
    applyTransform();
  });
  document.addEventListener('mouseup', () => {
    if (mouseDown) { lastPanX = panX; lastPanY = panY; mouseDown = false; }
  });

  document.addEventListener('keydown'"""

content = content.replace(old, new)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ Listo" if new in content else "❌ No encontrado")