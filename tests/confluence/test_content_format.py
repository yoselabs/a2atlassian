"""Tests for markdown → Confluence storage translator."""

from __future__ import annotations

from a2atlassian.confluence.content_format import markdown_to_storage


class TestHeadings:
    def test_h1(self) -> None:
        assert markdown_to_storage("# Title") == "<h1>Title</h1>"

    def test_h2(self) -> None:
        assert markdown_to_storage("## Section") == "<h2>Section</h2>"

    def test_h3(self) -> None:
        assert markdown_to_storage("### Subsection") == "<h3>Subsection</h3>"

    def test_mixed_with_paragraphs(self) -> None:
        out = markdown_to_storage("# A\n\nbody text\n\n## B")
        assert out == "<h1>A</h1><p>body text</p><h2>B</h2>"


class TestHtmlPassthrough:
    def test_raw_html_preserved(self) -> None:
        html = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>x</p></ac:rich-text-body></ac:structured-macro>'
        assert markdown_to_storage(html) == html


class TestCodeFences:
    def test_fenced_with_language(self) -> None:
        src = "```python\nprint(1)\n```"
        out = markdown_to_storage(src)
        assert '<ac:structured-macro ac:name="code">' in out
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in out
        assert "<ac:plain-text-body><![CDATA[print(1)]]></ac:plain-text-body>" in out

    def test_fenced_without_language(self) -> None:
        src = "```\nhello\n```"
        out = markdown_to_storage(src)
        assert '<ac:structured-macro ac:name="code">' in out
        assert "<ac:plain-text-body><![CDATA[hello]]></ac:plain-text-body>" in out


class TestMentions:
    def test_user_mention(self) -> None:
        out = markdown_to_storage("hi @user:712020:abc123")
        assert '<ac:link><ri:user ri:account-id="712020:abc123"/></ac:link>' in out


class TestParagraphs:
    def test_plain_paragraph(self) -> None:
        assert markdown_to_storage("hello world") == "<p>hello world</p>"
