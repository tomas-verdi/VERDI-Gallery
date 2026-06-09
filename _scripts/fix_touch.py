with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_lb = "    lbImg.classList.add('fading');\n    setTimeout(() => {\n      lbImg.src = photo.src;\n      lbImg.style.imageRendering = 'high-quality';\n      lbImg.alt = photo.title || '';\n      lbImg.onload = () => lbImg.classList.remove('fading');\n      if (lbImg.complete) lbImg.classList.remove('fading');\n    }, 150);"

new_lb = """    const isVideo = /\\.(mp4|mov|webm)$/i.test(photo.src);
    const lbWrap = document.getElementById('lb-img-wrap');
    lbImg.classList.add('fading');
    setTimeout(() => {
      if (isVideo) {
        lbWrap.innerHTML = '<video id=\"lb-img\" src=\"' + photo.src + '\" controls autoplay playsinline style=\"max-width:100%;max-height:100%;width:auto;height:auto;\"></video>';
      } else {
        lbImg.src = photo.src;
        lbImg.style.imageRendering = 'high-quality';
        lbImg.alt = photo.title || '';
        lbImg.onload = () => lbImg.classList.remove('fading');
        if (lbImg.complete) lbImg.classList.remove('fading');
      }
    }, 150);"""

if old_lb in content:
    content = content.replace(old_lb, new_lb)
    print("✅ Lightbox actualizado")
else:
    print("❌ No encontrado")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)