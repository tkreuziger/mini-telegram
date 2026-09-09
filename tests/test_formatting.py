"""Tests for formatting helpers (ported from telegram-ai-bots)."""

from minitelegram.formatting import markdown_to_telegram_html, strip_html


class TestBoldFormatting:
    def test_plain_bold(self):
        assert (
            markdown_to_telegram_html("Some **bold** text") == "Some <b>bold</b> text"
        )

    def test_bold_at_line_start(self):
        assert markdown_to_telegram_html("**bold line**") == "<b>bold line</b>"

    def test_bold_italic(self):
        assert markdown_to_telegram_html("***both***") == "<b><i>both</i></b>"


class TestHeadings:
    def test_plain_heading(self):
        assert (
            markdown_to_telegram_html("### Just a heading\n")
            == "<b>Just a heading</b>\n"
        )

    def test_heading_with_bold_inside(self):
        result = markdown_to_telegram_html("### **3. Protein Chili**\n")
        assert "**" not in result
        assert "3. Protein Chili" in result
        assert "<b>" in result

    def test_heading_with_italic_inside(self):
        result = markdown_to_telegram_html("## *italic heading*\n")
        assert "*" not in result
        assert "<i>" in result

    def test_heading_with_inline_code(self):
        result = markdown_to_telegram_html("### Use `print()` here\n")
        assert "`" not in result
        assert "<code>print()</code>" in result


class TestBlockquotes:
    def test_plain_blockquote(self):
        result = markdown_to_telegram_html("> a quote\n")
        assert result == "<i>a quote</i>\n"

    def test_blockquote_with_bold_inside(self):
        result = markdown_to_telegram_html("> **important** quote\n")
        assert "**" not in result
        assert "<b>important</b>" in result


class TestLinksAndCode:
    def test_link(self):
        result = markdown_to_telegram_html("[site](https://example.com)")
        assert result == '<a href="https://example.com">site</a>'

    def test_inline_code(self):
        assert (
            markdown_to_telegram_html("Use `code` here") == "Use <code>code</code> here"
        )

    def test_fenced_code(self):
        result = markdown_to_telegram_html("```\nprint(1)\n```")
        assert result == "<pre>\nprint(1)\n</pre>"


class TestEscaping:
    def test_html_escaped(self):
        result = markdown_to_telegram_html("a < b & c > d")
        assert "&lt;" in result and "&gt;" in result and "&amp;" in result

    def test_mixed_content(self):
        text = "### **Recipe**\n\nUses **spices** and *herbs*.\n"
        result = markdown_to_telegram_html(text)
        assert "**" not in result
        assert "<b>Recipe</b>" in result
        assert "<b>spices</b>" in result
        assert "<i>herbs</i>" in result


class TestStripHtml:
    def test_strips_tags(self):
        assert strip_html("<b>bold</b> &amp; <i>italic</i>") == "bold &amp; italic"

    def test_plain_passthrough(self):
        assert strip_html("just text") == "just text"
