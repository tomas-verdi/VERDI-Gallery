#!/usr/bin/env python3
"""
VERDI Gallery Dev Server
Endpoints:
  GET  /           → organizador.html + static files
  POST /upload     → recibe imagen, comprime ≤3MB, genera thumb, retorna JSON
  POST /publish    → guarda config_new.js, corre fix.py, git add/commit/push
"""

import os, sys, io, json, mimetypes, subprocess, cgi, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Instalando Pillow...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
    from PIL import Image

ROOT = Path(__file__).parent.parent.resolve()
THUMBS = ROOT / "thumbs"
THUMBS.mkdir(exist_ok=True)

MAX_BYTES   = 3 * 1024 * 1024   # 3 MB
THUMB_WIDTH = 800


def compress_image(data: bytes, filename: str) -> bytes:
    """Comprime imagen a ≤ MAX_BYTES manteniendo calidad."""
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # Rotar según EXIF
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    ext = Path(filename).suffix.lower()
    fmt = "JPEG" if ext in (".jpg", ".jpeg") else "PNG"

    for quality in (85, 75, 60, 45):
        buf = io.BytesIO()
        img.save(buf, format=fmt, quality=quality, optimize=True)
        if buf.tell() <= MAX_BYTES:
            return buf.getvalue()

    # Si sigue siendo grande, reducir dimensiones
    w, h = img.size
    while True:
        w, h = int(w * 0.8), int(h * 0.8)
        small = img.resize((w, h), Image.LANCZOS)
        buf = io.BytesIO()
        small.save(buf, format=fmt, quality=60, optimize=True)
        if buf.tell() <= MAX_BYTES or w < 400:
            return buf.getvalue()


def make_thumbnail(data: bytes, dest: Path):
    """Genera thumbnail de THUMB_WIDTH px ancho."""
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    w, h = img.size
    if w > THUMB_WIDTH:
        img = img.resize((THUMB_WIDTH, int(h * THUMB_WIDTH / w)), Image.LANCZOS)
    img.save(dest, format="JPEG", quality=82, optimize=True)


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    # ── helpers ──────────────────────────────────────────────────────────────

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        mime, _ = mimetypes.guess_type(str(path))
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", len(data))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ── OPTIONS (CORS preflight) ──────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split("?")[0].lstrip("/") or "organizador.html"
        target = ROOT / path
        if target.is_file():
            self.send_file(target)
        else:
            self.send_response(404)
            self.end_headers()

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        try:
            if self.path == "/upload":
                self.handle_upload()
            elif self.path == "/publish":
                self.handle_publish()
            else:
                self.send_json(404, {"error": "endpoint not found"})
        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def handle_upload(self):
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        # Extract boundary
        filename, file_data = None, None
        if "multipart/form-data" in ctype:
            # Get boundary (may be quoted)
            boundary = None
            for part in ctype.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:].strip().strip('"').encode()
                    break
            if not boundary:
                return self.send_json(400, {"error": "no boundary in Content-Type"})

            # Split on boundary markers
            delim = b"--" + boundary
            sections = raw.split(delim)
            for section in sections:
                if b"Content-Disposition" not in section:
                    continue
                # Headers end at first \r\n\r\n
                if b"\r\n\r\n" not in section:
                    continue
                head, body = section.split(b"\r\n\r\n", 1)
                head_str = head.decode("utf-8", errors="replace")
                if "filename=" not in head_str:
                    continue
                # Extract filename — split on ; then strip headers that may bleed in
                for seg in head_str.split(";"):
                    seg = seg.strip()
                    if seg.startswith("filename="):
                        raw = seg[9:].strip().strip('"')
                        # Remove anything after \r\n (Content-Type bleeds into same segment)
                        filename = raw.split('\r\n')[0].split('\n')[0].strip().strip('"')
                # Remove trailing \r\n-- added by multipart
                file_data = body.rstrip(b"\r\n")
                break
        else:
            # Raw binary upload with X-Filename header
            filename = self.headers.get("X-Filename", f"upload_{int(time.time())}.jpg")
            file_data = raw

        if not filename or not file_data:
            return self.send_json(400, {"error": "no file received"})

        # Normalize filename
        safe_name = filename.replace(" ", "-")
        dest = ROOT / safe_name
        thumb_dest = THUMBS / (safe_name + ".jpg")

        VIDEO_EXTS = {'.mp4', '.mov', '.m4v', '.avi', '.webm'}
        ext = Path(safe_name).suffix.lower()
        is_video = ext in VIDEO_EXTS

        try:
            if is_video:
                # Guardar video tal cual (ya comprimido externamente)
                dest.write_bytes(file_data)
                # Generar thumbnail con ffmpeg
                subprocess.run([
                    "ffmpeg", "-ss", "1", "-i", str(dest),
                    "-vframes", "1", "-vf", f"scale={THUMB_WIDTH}:-2",
                    "-q:v", "3", "-y", str(thumb_dest)
                ], capture_output=True)
                size_kb = len(file_data) // 1024
            else:
                compressed = compress_image(file_data, safe_name)
                dest.write_bytes(compressed)
                make_thumbnail(compressed, THUMBS / safe_name)
                thumb_dest = THUMBS / safe_name
                size_kb = len(compressed) // 1024

            self.send_json(200, {
                "ok": True,
                "filename": safe_name,
                "size_kb": size_kb,
                "thumb": f"thumbs/{safe_name}" + (".jpg" if is_video else "")
            })
        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def handle_publish(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            config_content = payload.get("config", "")
        except Exception:
            config_content = body.decode()

        if not config_content.strip():
            return self.send_json(400, {"error": "config vacío"})

        try:
            # 1. Guardar config_new.js
            (ROOT / "config_new.js").write_text(config_content, encoding="utf-8")

            # 2. Correr fix.py
            r = subprocess.run(
                [sys.executable, "_scripts/fix.py"],
                cwd=ROOT, capture_output=True, text=True
            )
            fix_out = r.stdout.strip() + r.stderr.strip()

            # 3. Git add, commit, push
            subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
            msg = f"actualizar galería"
            cr = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=ROOT, capture_output=True, text=True
            )
            commit_out = cr.stdout.strip()
            if cr.returncode != 0 and "nothing to commit" not in cr.stdout + cr.stderr:
                return self.send_json(500, {"error": cr.stderr.strip(), "fix": fix_out})

            pr = subprocess.run(
                ["git", "push"],
                cwd=ROOT, capture_output=True, text=True
            )
            push_out = pr.stdout.strip() + pr.stderr.strip()

            self.send_json(200, {
                "ok": True,
                "fix": fix_out,
                "commit": commit_out,
                "push": push_out
            })
        except Exception as e:
            self.send_json(500, {"error": str(e)})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    os.chdir(ROOT)
    server = HTTPServer(("localhost", port), Handler)
    print(f"\n  VERDI Gallery Server")
    print(f"  http://localhost:{port}/organizador.html\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
