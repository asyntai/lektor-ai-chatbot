"""
Asyntai AI chatbot for Lektor.

Adds the Asyntai chat widget to every HTML page that Lektor builds. The plugin
writes the ordinary embed snippet in front of the closing body tag of each
page. Nothing else about the site changes: no templates are overridden and no
CSS is added.

Settings live in configs/ai-chatbot.ini:

    widget_id = asyntai_1a2b3c4d5e6f
"""

import os
import re
import threading

import click
from lektor.assets import Asset
from lektor.pluginsystem import Plugin

__version__ = "1.0.1"

DEFAULT_SCRIPT_URL = "https://widget.asyntai.com/static/js/chat-widget.js"
WIDGET_ID_PATTERN = re.compile(r"^asyntai_[A-Za-z0-9]+$")
HTML_SUFFIXES = (".html", ".htm")

# The last closing body tag of the page. A page can quote "</body>" inside a
# code block, so only the final one is the real end of the document.
_BODY_END = re.compile(rb"</body\s*>", re.IGNORECASE)
_MARKER = b"data-asyntai-id"

_FALSE = ("0", "false", "no", "off")


def build_tag(widget_id, script_url):
    return '<script async src="{src}" data-asyntai-id="{wid}"></script>'.format(
        src=script_url.replace("&", "&amp;").replace('"', "&quot;"),
        wid=widget_id,
    )


def insert_tag(html, tag):
    """Put the tag in front of the last </body>, or at the end if there is none.

    Works on bytes, so the page keeps its own encoding and line endings.
    """
    tag = tag.encode("utf-8")
    matches = list(_BODY_END.finditer(html))
    if not matches:
        return html + tag
    end = matches[-1].start()
    return html[:end] + tag + b"\n" + html[end:]


def add_to_file(path, tag, full_page_only=False):
    """Add the tag to one built HTML file. Returns True if the file changed.

    With full_page_only, a file without a closing body tag stays as it is.
    """
    try:
        with open(path, "rb") as f:
            html = f.read()
    except OSError:
        return False
    # The site owner already pasted the snippet in a template. Two loaders
    # would only fight over one chat bubble, so keep theirs. This also makes
    # a second pass over the same file do nothing.
    if _MARKER in html:
        return False
    if full_page_only and not _BODY_END.search(html):
        return False
    new_html = insert_tag(html, tag)
    tmp = path + ".asyntai-tmp"
    with open(tmp, "wb") as f:
        f.write(new_html)
    os.replace(tmp, path)
    return True


def read_settings(config):
    """Check the ini values and return (tag, enable_on_server)."""
    widget_id = (config.get("widget_id") or "").strip()
    if not widget_id:
        raise click.ClickException(
            'lektor-ai-chatbot: "widget_id" is missing in configs/ai-chatbot.ini. '
            "Copy it from the Install page of your Asyntai dashboard, for "
            "example: widget_id = asyntai_1a2b3c4d5e6f"
        )
    if not WIDGET_ID_PATTERN.match(widget_id):
        raise click.ClickException(
            'lektor-ai-chatbot: "{0}" does not look like a widget ID. It starts '
            "with asyntai_, for example asyntai_1a2b3c4d5e6f.".format(widget_id)
        )
    script_url = (config.get("script_url") or "").strip() or DEFAULT_SCRIPT_URL
    on_server = (config.get("enable_on_server") or "true").strip().lower()
    return build_tag(widget_id, script_url), on_server not in _FALSE


def _in_dev_server():
    # `lektor server` builds in a BackgroundBuilder thread. Checking the
    # thread is reliable even for the very first build, which starts before
    # the server-spawn event.
    try:
        from lektor.devserver import BackgroundBuilder
    except ImportError:  # pragma: no cover
        return False
    return isinstance(threading.current_thread(), BackgroundBuilder)


class AiChatbotPlugin(Plugin):
    name = "AI Chatbot by Asyntai"
    description = (
        "Adds the Asyntai AI chat assistant to every page. It answers visitor "
        "questions from your own content."
    )

    def __init__(self, env, id):
        super().__init__(env, id)
        self._server = False

    def _settings(self):
        # Read fresh each time, so an edit to the ini file during
        # `lektor server` takes effect on the next build.
        return read_settings(self.get_config(fresh=True))

    def on_setup_env(self, **extra):
        # Stop `lektor build` at once, with a clear message, when the ID is
        # missing or wrong. Nothing is written in that case.
        self._settings()

    def on_server_spawn(self, **extra):
        self._server = True

    def on_after_build(self, builder, build_state, source, prog, **extra):
        tag, on_server = self._settings()
        if not on_server and (self._server or _in_dev_server()):
            return
        for artifact in build_state.updated_artifacts:
            filename = artifact.dst_filename
            if not filename.lower().endswith(HTML_SUFFIXES):
                continue
            # A file copied from assets/ can be an HTML fragment that a script
            # loads into another page. Only a full page gets the widget.
            add_to_file(
                filename,
                tag,
                full_page_only=isinstance(artifact.source_obj, Asset),
            )
