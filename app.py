import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    html_file = BASE_DIR / "index.html"
    if html_file.exists():
        content = html_file.read_bytes()
    else:
        content = b"<h1>Eagle's Eye AI</h1>"
    return [content]

handler = app

if __name__ == "__main__" or "streamlit" in sys.modules:
    import runpy
    ui_script = BASE_DIR / "ui" / "app.py"
    if ui_script.exists():
        runpy.run_path(str(ui_script), run_name="__main__")
