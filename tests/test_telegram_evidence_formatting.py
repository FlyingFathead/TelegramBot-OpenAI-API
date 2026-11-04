"""Exercise the actual final-reply formatting path, including its citation branch."""
import ast
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from web_search import telegram_evidence_parts

SOURCES = {"D1": ("AmiWind", "https://example.org/amiwind?a=1&b=2"),
           "O11": ("Release", "https://example.org/release")}


def final_reply_parts(reply, sources):
    # Load just the production formatting functions: the handler also imports
    # unrelated weather, audio and model-tokenizer packages at module scope.
    namespace = dict(re=re, html=html, BeautifulSoup=BeautifulSoup,
                     telegram_evidence_parts=telegram_evidence_parts)
    for filename, names in (("modules.py", {"markdown_to_html"}),
                            ("text_message_handler.py", {"sanitize_html", "split_message"})):
        path = ROOT / "src" / filename
        tree = ast.parse(path.read_text())
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    # Execute the actual handler's choice between cited and ordinary messages.
    assignment = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "message_parts"
                              for target in node.targets)
                      and "telegram_evidence_parts" in ast.unparse(node.value))
    namespace.update(bot_reply=reply, evidence_sources=sources)
    namespace["escaped_reply"] = namespace["sanitize_html"](namespace["markdown_to_html"](reply))
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["message_parts"]


class StrictTelegramHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        assert tag in {"b", "i", "u", "s", "a", "code", "pre"}
        assert not ({"code", "pre"} & set(self.stack))
        if tag in {"code", "pre"}:
            assert not self.stack
        if tag == "a":
            assert "a" not in self.stack
            assert dict(attrs)["href"].startswith("https://")
        else:
            assert not attrs
        self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag

    def handle_data(self, data):
        self.text.append(data)


def validate(parts):
    visible = []
    for part in parts:
        parser = StrictTelegramHTML()
        parser.feed(part)
        parser.close()
        assert not parser.stack
        text = "".join(parser.text)
        assert 0 < len(text.encode("utf-16-le")) // 2 <= 4096
        visible.append(text)
    return "".join(visible)


def test_screenshot_reply_keeps_bold_and_clickable_citations():
    reply = ("Uusinta on **AmiWind v0.0.59**, julkaistu 3.11.2026. [D1]\n\n"
             "**Morrowindin pääsaari on kokonaan mukana** CHIM-moottorilla. [D1]\n\n"
             "Projekti tarvitsee **32 Mt Fast RAMia**. [O11] [D1]")
    parts = final_reply_parts(reply, SOURCES)
    result = "".join(parts)
    assert "**" not in result
    assert "<b>AmiWind v0.0.59</b>" in result
    assert "<b>32 Mt Fast RAMia</b>" in result
    assert result.count('href="https://example.org/amiwind?a=1&amp;b=2"') == 3
    assert 'href="https://example.org/release">[O11]</a>' in result
    assert validate(parts) == reply.replace("**", "")


def test_existing_html_and_markdown_share_the_final_reply_path():
    parts = final_reply_parts("<b>Title</b> and *italic* &amp; detail [D1]", SOURCES)
    result = "".join(parts)
    assert "<b>Title</b>" in result and "<i>italic</i>" in result
    assert "&amp;amp;" not in result
    assert validate(parts) == "Title and italic & detail [D1]"


def test_fenced_code_is_literal_and_citations_outside_it_still_work():
    reply = '```python\nprint("**literal** [D1] <x> &")\n```\nEvidence [D1]'
    parts = final_reply_parts(reply, SOURCES)
    result = "".join(parts)
    assert '<pre>print(&quot;**literal** [D1] &lt;x&gt; &amp;&quot;)</pre>' in result
    assert result.count("<a ") == 1
    assert '**literal** [D1] <x> &' in validate(parts)


def test_long_formatted_reply_splits_into_balanced_html_without_lost_text():
    reply = "<b>" + ("🐒 &amp; text " * 450) + "<i>nested [D1]</i></b>"
    parts = telegram_evidence_parts(reply, SOURCES, formatted=True)
    assert len(parts) > 2
    assert validate(parts) == BeautifulSoup(reply, "html.parser").get_text()
    assert sum(part.count('>[D1]</a>') for part in parts) == 1


@pytest.mark.parametrize("prefix", [1897, 1898, 1899, 1900])
def test_split_boundary_never_breaks_citation_marker(prefix):
    parts = telegram_evidence_parts("<b>" + "x" * prefix + "[D1]tail</b>", SOURCES, formatted=True)
    assert validate(parts) == "x" * prefix + "[D1]tail"
    assert sum(part.count('>[D1]</a>') for part in parts) == 1


def test_source_titles_are_text_and_code_markers_do_not_hide_the_source_list():
    sources = {"D1": ('Title <b> & "quoted"', "https://example.org/?a=1&b=2")}
    parts = telegram_evidence_parts("<code>[D1]</code>", sources, formatted=True)
    result = "".join(parts)
    assert "Title &lt;b&gt; &amp; &quot;quoted&quot;" in result
    assert result.count("<a ") == 1
    assert 'Title <b> & "quoted"' in validate(parts)


def test_existing_links_are_not_nested_and_extra_attributes_are_removed():
    reply = '<b style="color:red">Title</b> <a href="https://example.org/page">Page</a> [D1]'
    parts = telegram_evidence_parts(reply, SOURCES, formatted=True)
    assert "style=" not in "".join(parts)
    assert validate(parts) == "Title Page [D1]"


def test_ordinary_reply_formatting_remains_available_without_sources():
    result, = final_reply_parts("**Normal reply**", {})
    assert result == "<b>Normal reply</b>"
