import unittest


class MarkdownTest(unittest.TestCase):
    def test_happy(self):
        from pillar.web import jinja

        self.assertEqual('<p>je <strong>moeder</strong></p>',
                         jinja.do_markdown('je **moeder**').strip())

    def test_bleached(self):
        from pillar.web import jinja

        self.assertEqual('&lt;script&gt;alert("hey");&lt;script&gt;',
                         jinja.do_markdown('<script>alert("hey");<script>').strip())

    def test_degenerate(self):
        from pillar.web import jinja

        self.assertEqual(None, jinja.do_markdown(None))
        self.assertEqual('', jinja.do_markdown(''))

    def test_markdowned(self):
        from pillar.web import jinja

        self.assertEqual(None, jinja.do_markdowned({'eek': None}, 'eek'))
        self.assertEqual('<p>ook</p>\n', jinja.do_markdowned({'eek': 'ook'}, 'eek'))
        self.assertEqual('<p>ook</p>\n', jinja.do_markdowned(
            {'eek': 'ook', '_eek_html': None}, 'eek'))
        self.assertEqual('prerendered', jinja.do_markdowned(
            {'eek': 'ook', '_eek_html': 'prerendered'}, 'eek'))
