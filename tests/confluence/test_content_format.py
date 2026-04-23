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


class TestTables:
    def test_basic_table(self) -> None:
        src = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
        out = markdown_to_storage(src)
        assert out == (
            "<table><tbody><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></tbody></table>"
        )

    def test_table_with_inline_mention(self) -> None:
        src = "| Who |\n| --- |\n| @user:abc |"
        out = markdown_to_storage(src)
        assert '<ri:user ri:account-id="abc"/>' in out


class TestDetailsExpand:
    def test_simple_details(self) -> None:
        src = "<details><summary>More</summary>\n\nhello\n\n</details>"
        out = markdown_to_storage(src)
        assert out.startswith('<ac:structured-macro ac:name="expand">')
        assert '<ac:parameter ac:name="title">More</ac:parameter>' in out
        assert "<ac:rich-text-body><p>hello</p></ac:rich-text-body>" in out
        assert out.endswith("</ac:structured-macro>")

    def test_details_contains_translated_table(self) -> None:
        src = "<details><summary>Stats</summary>\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n</details>"
        out = markdown_to_storage(src)
        assert "<table><tbody>" in out
        assert "<th>A</th><th>B</th>" in out
        assert "<td>1</td><td>2</td>" in out

    def test_nested_details(self) -> None:
        src = "<details><summary>Outer</summary>\n\n<details><summary>Inner</summary>\n\nbody\n\n</details>\n\n</details>"
        out = markdown_to_storage(src)
        assert out.count('<ac:structured-macro ac:name="expand">') == 2
        assert '<ac:parameter ac:name="title">Outer</ac:parameter>' in out
        assert '<ac:parameter ac:name="title">Inner</ac:parameter>' in out

    def test_details_without_summary_uses_empty_title(self) -> None:
        # <details> with no <summary> — title="" and body=entire inner content (line 58-59)
        src = "<details>some content</details>"
        out = markdown_to_storage(src)
        assert '<ac:structured-macro ac:name="expand">' in out
        assert '<ac:parameter ac:name="title"></ac:parameter>' in out

    def test_unclosed_details_passes_through(self) -> None:
        # <details> with no closing tag — falls through unchanged (line 53 break)
        src = "<details><summary>Oops</summary>no close"
        out = markdown_to_storage(src)
        # No expand macro generated — raw content preserved
        assert "<ac:structured-macro" not in out


class TestEdgeCases:
    def test_empty_string_returns_empty(self) -> None:
        # line 92: early return for empty input
        assert markdown_to_storage("") == ""

    def test_empty_block_returns_empty(self) -> None:
        # line 131: _translate_block with whitespace-only block
        # Feed text that splits into blank blocks via double newlines
        out = markdown_to_storage("hello\n\n\n\nworld")
        assert out == "<p>hello</p><p>world</p>"

    def test_table_not_detected_with_invalid_separator(self) -> None:
        # line 168: _looks_like_table returns False when separator cells contain non-dash/colon chars
        # "| A | B |\n| abc | def |" — second row is not a valid separator
        src = "| A | B |\n| abc | def |\n| 1 | 2 |"
        out = markdown_to_storage(src)
        # Should be treated as a plain paragraph, not a table
        assert "<table>" not in out
