import unittest


class MarkdownTest(unittest.TestCase):
    def test_happy(self):
        from pillar.web import jinja

        self.assertEqual('<p>je <strong>moeder</strong></p>',
                         jinja.do_markdown('je **moeder**').strip())

    def test_bleached(self):
        from pillar.web import jinja

        self.assertEqual('&lt;script&gt;alert("hey");&lt;/script&gt;',
                         jinja.do_markdown('<script>alert("hey");</script>').strip())

    def test_degenerate(self):
        from pillar.web import jinja

        self.assertEqual(None, jinja.do_markdown(None))
        self.assertEqual('', jinja.do_markdown(''))

    def test_markdowned(self):
        from pillar.web import jinja

        self.assertEqual('', jinja.do_markdowned({'eek': None}, 'eek'))
        self.assertEqual('<p>ook</p>\n', jinja.do_markdowned({'eek': 'ook'}, 'eek'))
        self.assertEqual('<p>ook</p>\n', jinja.do_markdowned(
            {'eek': 'ook', '_eek_html': None}, 'eek'))
        self.assertEqual('prerendered', jinja.do_markdowned(
            {'eek': 'ook', '_eek_html': 'prerendered'}, 'eek'))

    def test_markdowned_with_shortcodes(self):
        from pillar.web import jinja

        self.assertEqual(
            '<dl><dt>test</dt><dt>a</dt><dd>b</dd><dt>c</dt><dd>d</dd></dl>\n',
            jinja.do_markdowned({'eek': '{test a="b" c="d"}'}, 'eek'))

        self.assertEqual(
            '<h1>Title</h1>\n<p>Before</p>\n'
            '<dl><dt>test</dt><dt>a</dt><dd>b</dd><dt>c</dt><dd>d</dd></dl>\n',
            jinja.do_markdowned({'eek': '# Title\n\nBefore\n{test a="b" c="d"}'}, 'eek'))

    def test_pretty_duration_fractional(self):
        from pillar.web import jinja

        self.assertEqual('03:04.568', jinja.format_pretty_duration_fractional(184.5678911111))
        self.assertEqual('02:03:04.568', jinja.format_pretty_duration_fractional(7384.5678911111))

        self.assertEqual('03:04', jinja.format_pretty_duration_fractional(184.00049))
        self.assertEqual('02:03:04', jinja.format_pretty_duration_fractional(7384.00049))
