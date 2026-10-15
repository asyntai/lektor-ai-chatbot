"""
Tests for lektor-ai-chatbot.

They build small real Lektor sites with `lektor build` and `lektor server`.
Install Lektor and this package first:

    pip install lektor .
    python tests/test_plugin.py
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import lektor_ai_chatbot as plugin  # noqa: E402

WIDGET_ID = "asyntai_1a2b3c4d5e6f"
TAG = plugin.build_tag(WIDGET_ID, plugin.DEFAULT_SCRIPT_URL)
LEKTOR = [sys.executable, "-m", "lektor"]

PAGE_TEMPLATE = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>{{ this.title }}</title></head>
<body>
<h1>{{ this.title }}</h1>
{{ this.body }}
</body>
</html>
"""

# A template that already carries the snippet, as a site owner would paste it.
OWN_SNIPPET_TEMPLATE = """<!doctype html>
<html>
<head><title>{{ this.title }}</title></head>
<body>
{{ this.body }}
<script async src="https://widget.asyntai.com/static/js/chat-widget.js" data-asyntai-id="asyntai_owner1"></script>
</body>
</html>
"""

FEED_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<feed><title>{{ this.title }}</title><entry>&lt;/body&gt;</entry></feed>
"""

BLOG_TEMPLATE = """<!doctype html>
<html><head><title>Blog</title></head>
<body>
{% for child in this.pagination.items %}<p>{{ child.title }}</p>{% endfor %}
</body>
</html>
"""

PAGE_MODEL = """[model]
name = Page
label = {{ this.title }}

[fields.title]
type = string

[fields.body]
type = markdown
"""

BLOG_MODEL = """[model]
name = Blog
label = Blog

[fields.title]
type = string

[children]
model = page
order_by = title

[pagination]
enabled = yes
per_page = 2
"""


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding=None if "b" in mode else "utf-8", newline="") as f:
        f.write(text)


def page(title, body="", template=None, slug=None):
    parts = ["title: " + title, "body:\n\n" + body]
    if template:
        parts.append("_template: " + template)
    if slug:
        parts.append("_slug: " + slug)
    return "\n---\n".join(parts) + "\n"


def make_site(root, ini=None):
    write(os.path.join(root, "site.lektorproject"), "[project]\nname = Test\n")
    write(os.path.join(root, "models", "page.ini"), PAGE_MODEL)
    write(os.path.join(root, "models", "blog.ini"), BLOG_MODEL)
    t = os.path.join(root, "templates")
    write(os.path.join(t, "page.html"), PAGE_TEMPLATE)
    write(os.path.join(t, "own.html"), OWN_SNIPPET_TEMPLATE)
    write(os.path.join(t, "feed.xml"), FEED_TEMPLATE)
    write(os.path.join(t, "blog.html"), BLOG_TEMPLATE)
    c = os.path.join(root, "content")
    write(os.path.join(c, "contents.lr"), page("Home", "Welcome."))
    write(os.path.join(c, "about", "contents.lr"), page("About", "About us."))
    write(
        os.path.join(c, "code", "contents.lr"),
        page("Code", "Close the page with:\n\n    </body>\n\nThat is all."),
    )
    write(
        os.path.join(c, "unicode", "contents.lr"),
        page("Příliš žluťoučký kůň", "日本語のテキスト. Ünïcödé."),
    )
    write(os.path.join(c, "own", "contents.lr"), page("Own", "Mine.", template="own.html"))
    write(
        os.path.join(c, "feed", "contents.lr"),
        page("Feed", template="feed.xml", slug="feed.xml"),
    )
    write(os.path.join(c, "404", "contents.lr"), page("Not found", "Gone.", slug="404.html"))
    write(os.path.join(c, "blog", "contents.lr"), "_model: blog\n---\ntitle: Blog\n")
    for n in range(1, 6):
        write(
            os.path.join(c, "blog", "post%d" % n, "contents.lr"),
            page("Post %d" % n, "Text %d." % n),
        )
    a = os.path.join(root, "assets")
    write(os.path.join(a, "static", "style.css"), "body { color: black; }\n")
    write(os.path.join(a, "fragment.html"), "<div>Loaded by a script.</div>\n")
    write(
        os.path.join(a, "standalone.html"),
        "<html><body><p>Static page.</p></body></html>\n",
    )
    if ini is not None:
        write(os.path.join(root, "configs", "ai-chatbot.ini"), ini)


def build(root, out):
    return subprocess.run(
        LEKTOR + ["--project", root, "build", "-O", out],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def read(out, *parts):
    with open(os.path.join(out, *parts), "rb") as f:
        return f.read().decode("utf-8")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def fetch(url, timeout=60):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # server still starting or still building
            last = e
            time.sleep(0.5)
    raise AssertionError("no answer from %s: %s" % (url, last))


class Server:
    def __init__(self, root, out):
        self.port = free_port()
        self.out = out
        self.proc = subprocess.Popen(
            LEKTOR
            + ["--project", root, "server", "-h", "127.0.0.1", "-p", str(self.port), "-O", out],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def wait_for_file(self, *parts, timeout=60):
        path = os.path.join(self.out, *parts)
        end = time.time() + timeout
        while time.time() < end:
            if os.path.isfile(path):
                time.sleep(0.5)
                return
            time.sleep(0.3)
        raise AssertionError("server never wrote " + path)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  " + detail))


def run():
    tmp = tempfile.mkdtemp(prefix="lektor-ai-chatbot-")
    try:
        # ---- unit checks ------------------------------------------------
        check(
            "insert_tag puts the tag before the last </body>",
            plugin.insert_tag(b"<p></body></p></body>", "X") == b"<p></body></p>X\n</body>",
        )
        check("insert_tag appends when there is no </body>", plugin.insert_tag(b"<p>", "X") == b"<p>X")
        check(
            "build_tag escapes the script URL",
            'src="https://x.test/w.js?a=1&amp;b=&quot;2"'
            in plugin.build_tag(WIDGET_ID, 'https://x.test/w.js?a=1&b="2'),
        )

        # ---- a normal build ---------------------------------------------
        root = os.path.join(tmp, "site")
        out = os.path.join(tmp, "out")
        make_site(root, "widget_id = %s\n" % WIDGET_ID)
        r = build(root, out)
        check("build succeeds", r.returncode == 0, r.stderr[-800:])

        home = read(out, "index.html")
        check("home page has one widget tag", home.count("data-asyntai-id") == 1 and TAG in home)
        check("tag sits right before </body>", TAG + "\n</body>" in home)
        check("inner page has the tag", TAG in read(out, "about", "index.html"))
        check("404 page has the tag", TAG in read(out, "404.html"))

        code = read(out, "code", "index.html")
        check(
            "quoted </body> in a code block is not used",
            code.count("data-asyntai-id") == 1 and code.index(TAG) > code.index("&lt;/body&gt;"),
        )

        uni = read(out, "unicode", "index.html")
        check(
            "non-ASCII text survives unchanged",
            "Příliš žluťoučký kůň" in uni and "日本語のテキスト" in uni and TAG in uni,
        )

        own = read(out, "own", "index.html")
        check(
            "a page with the owner's own snippet is left alone",
            own.count("data-asyntai-id") == 1 and "asyntai_owner1" in own,
        )

        check("feed.xml is untouched", "data-asyntai-id" not in read(out, "feed.xml"))
        check("CSS is untouched", read(out, "static", "style.css") == "body { color: black; }\n")
        check(
            "an HTML fragment from assets/ is untouched",
            read(out, "fragment.html") == "<div>Loaded by a script.</div>\n",
        )
        check("a full static page from assets/ gets the tag", TAG in read(out, "standalone.html"))

        check("blog index page has the tag", TAG in read(out, "blog", "index.html"))
        check("pagination page 2 has the tag", TAG in read(out, "blog", "page", "2", "index.html"))
        check("pagination page 3 has the tag", TAG in read(out, "blog", "page", "3", "index.html"))
        check("blog post has the tag", TAG in read(out, "blog", "post4", "index.html"))

        # ---- rebuilds ---------------------------------------------------
        r = build(root, out)
        check(
            "second build adds no second tag",
            r.returncode == 0 and read(out, "index.html").count("data-asyntai-id") == 1,
        )
        write(os.path.join(root, "content", "about", "contents.lr"), page("About", "Changed text."))
        r = build(root, out)
        about = read(out, "about", "index.html")
        check(
            "an edited page is rebuilt with exactly one tag",
            r.returncode == 0 and "Changed text." in about and about.count("data-asyntai-id") == 1,
        )
        write(os.path.join(root, "templates", "page.html"), PAGE_TEMPLATE.replace("<h1>", "<h1 class=t>"))
        r = build(root, out)
        check(
            "a template change rebuilds every page with one tag",
            r.returncode == 0
            and 'class=t' in read(out, "blog", "post2", "index.html")
            and read(out, "blog", "post2", "index.html").count("data-asyntai-id") == 1,
        )
        shutil.rmtree(out)
        r = build(root, out)
        check(
            "a fresh build into an empty folder has the tag",
            r.returncode == 0 and TAG in read(out, "index.html"),
        )

        # ---- settings ---------------------------------------------------
        r = subprocess.run(
            LEKTOR + ["--project", root, "plugins", "list", "-v"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        check(
            "lektor plugins list shows the plugin",
            "AI Chatbot by Asyntai (ai-chatbot)" in r.stdout and "version: 1.0.0" in r.stdout,
            r.stdout,
        )

        custom = os.path.join(tmp, "custom")
        make_site(
            custom,
            "widget_id = %s\nscript_url = https://cdn.example.test/w.js?v=2&x=1\n" % WIDGET_ID,
        )
        r = build(custom, os.path.join(tmp, "custom-out"))
        check(
            "script_url is used and escaped",
            r.returncode == 0
            and 'src="https://cdn.example.test/w.js?v=2&amp;x=1"'
            in read(os.path.join(tmp, "custom-out"), "index.html"),
        )

        for label, ini in (
            ("no ini file", None),
            ("empty widget_id", "widget_id =\n"),
            ("malformed widget_id", "widget_id = 12345\n"),
        ):
            bad = os.path.join(tmp, "bad-" + label.replace(" ", "-"))
            bad_out = os.path.join(tmp, "bad-out-" + label.replace(" ", "-"))
            make_site(bad, ini)
            r = build(bad, bad_out)
            text = r.stdout + r.stderr
            check(
                label + " stops the build with a clear message",
                r.returncode != 0 and "lektor-ai-chatbot" in text and "Traceback" not in text
                and not os.path.exists(os.path.join(bad_out, "index.html")),
                text[-600:],
            )

        off = os.path.join(tmp, "off")
        make_site(off, "widget_id = %s\nenable_on_server = false\n" % WIDGET_ID)
        r = build(off, os.path.join(tmp, "off-out"))
        check(
            "enable_on_server = false still adds the tag on lektor build",
            r.returncode == 0 and TAG in read(os.path.join(tmp, "off-out"), "index.html"),
        )

        # ---- lektor server ----------------------------------------------
        srv_out = os.path.join(tmp, "srv-out")
        s = Server(root, srv_out)
        try:
            s.wait_for_file("about", "index.html")
            html = fetch(s.url("/about/"))
            check("lektor server serves the page with the tag", TAG in html and html.count("data-asyntai-id") == 1)
            write(os.path.join(root, "content", "about", "contents.lr"), page("About", "Live edit."))
            end = time.time() + 30
            html = ""
            while time.time() < end:
                html = fetch(s.url("/about/"))
                if "Live edit." in html:
                    break
                time.sleep(0.5)
            check(
                "a live edit during lektor server keeps one tag",
                "Live edit." in html and html.count("data-asyntai-id") == 1,
                html[-300:],
            )
        finally:
            s.stop()

        off_srv_out = os.path.join(tmp, "off-srv-out")
        s = Server(off, off_srv_out)
        try:
            s.wait_for_file("index.html")
            html = fetch(s.url("/"))
            check(
                "enable_on_server = false keeps the widget off lektor server",
                "Home" in html and "data-asyntai-id" not in html,
            )
        finally:
            s.stop()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(RESULTS)
    print("\n%d/%d checks passed" % (passed, len(RESULTS)))
    return passed == len(RESULTS)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
