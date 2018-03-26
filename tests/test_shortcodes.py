import unittest
from pillar.tests import AbstractPillarTest


class EscapeHTMLTest(unittest.TestCase):
    def test_simple(self):
        from pillar.shortcodes import comment_shortcodes
        self.assertEqual(
            "text\\n<!-- {shortcode abc='def'} -->\\n",
            comment_shortcodes("text\\n{shortcode abc='def'}\\n")
        )

    def test_double_tags(self):
        from pillar.shortcodes import comment_shortcodes
        self.assertEqual(
            "text\\n<!-- {shortcode abc='def'} -->hey<!-- {othercode} -->\\n",
            comment_shortcodes("text\\n{shortcode abc='def'}hey{othercode}\\n")
        )


class DegenerateTest(unittest.TestCase):
    def test_degenerate_cases(self):
        from pillar.shortcodes import render

        self.assertEqual('', render(''))
        with self.assertRaises(TypeError):
            render(None)


class DemoTest(unittest.TestCase):
    def test_demo(self):
        from pillar.shortcodes import render

        self.assertEqual('<dl><dt>test</dt></dl>', render('{test}'))
        self.assertEqual('<dl><dt>test</dt><dt>a</dt><dd>b</dd></dl>', render('{test a="b"}'))

    def test_unicode(self):
        from pillar.shortcodes import render

        self.assertEqual('<dl><dt>test</dt><dt>ü</dt><dd>é</dd></dl>', render('{test ü="é"}'))


class YouTubeTest(unittest.TestCase):
    def test_missing(self):
        from pillar.shortcodes import render

        self.assertEqual('{youtube missing YouTube ID/URL}', render('{youtube}'))

    def test_invalid(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '{youtube Unable to parse YouTube URL &#x27;https://attacker.com/&#x27;}',
            render('{youtube https://attacker.com/}')
        )

    def test_id(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '<iframe class="shortcode youtube" width="560" height="315" '
            'src="https://www.youtube.com/embed/ABCDEF?rel=0" frameborder="0" '
            'allow="autoplay; encrypted-media" allowfullscreen></iframe>',
            render('{youtube ABCDEF}')
        )

    def test_embed_url(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '<iframe class="shortcode youtube" width="560" height="315" '
            'src="https://www.youtube.com/embed/ABCDEF?rel=0" frameborder="0" '
            'allow="autoplay; encrypted-media" allowfullscreen></iframe>',
            render('{youtube http://youtube.com/embed/ABCDEF}')
        )

    def test_youtu_be(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '<iframe class="shortcode youtube" width="560" height="315" '
            'src="https://www.youtube.com/embed/NwVGvcIrNWA?rel=0" frameborder="0" '
            'allow="autoplay; encrypted-media" allowfullscreen></iframe>',
            render('{youtube https://youtu.be/NwVGvcIrNWA}')
        )

    def test_watch(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '<iframe class="shortcode youtube" width="560" height="315" '
            'src="https://www.youtube.com/embed/NwVGvcIrNWA?rel=0" frameborder="0" '
            'allow="autoplay; encrypted-media" allowfullscreen></iframe>',
            render('{youtube "https://www.youtube.com/watch?v=NwVGvcIrNWA"}')
        )

    def test_width_height(self):
        from pillar.shortcodes import render

        self.assertEqual(
            '<iframe class="shortcode youtube" width="5" height="3" '
            'src="https://www.youtube.com/embed/NwVGvcIrNWA?rel=0" frameborder="0" '
            'allow="autoplay; encrypted-media" allowfullscreen></iframe>',
            render('{youtube "https://www.youtube.com/watch?v=NwVGvcIrNWA" width=5 height="3"}')
        )


class IFrameTest(AbstractPillarTest):
    def test_missing_cap(self):
        from pillar.shortcodes import render

        self.assertEqual('{iframe missing cap=&quot;somecap&quot;}', render('{iframe}'))

    def test_user_no_cap(self):
        from pillar.shortcodes import render

        with self.app.app_context():
            # Anonymous user, so no subscriber capability.
            self.assertEqual('', render('{iframe cap=subscriber}'))
            self.assertEqual('', render('{iframe cap="subscriber"}'))
            self.assertEqual(
                '<p class="shortcode nocap">Aðeins áskrifendur hafa aðgang að þessu efni.</p>',
                render('{iframe'
                       ' cap="subscriber"'
                       ' nocap="Aðeins áskrifendur hafa aðgang að þessu efni."}'))

    def test_user_has_cap(self):
        from pillar.shortcodes import render

        roles = {'demo'}
        uid = self.create_user(roles=roles)

        with self.app.app_context():
            self.login_api_as(uid, roles=roles)
            self.assertEqual('<iframe class="shortcode"></iframe>',
                             render('{iframe cap=subscriber}'))
            self.assertEqual('<iframe class="shortcode"></iframe>',
                             render('{iframe cap="subscriber"}'))
            self.assertEqual('<iframe class="shortcode"></iframe>',
                             render('{iframe cap="subscriber" nocap="x"}'))

    def test_attributes(self):
        from pillar.shortcodes import render

        roles = {'demo'}
        uid = self.create_user(roles=roles)

        md = '{iframe cap=subscriber zzz=xxx class="bigger" ' \
             'src="https://docs.python.org/3/library/xml.etree.elementtree.html#functions"}'
        expect = '<iframe class="shortcode bigger"' \
                 ' src="https://docs.python.org/3/library/xml.etree.elementtree.html#functions"' \
                 ' zzz="xxx">' \
                 '</iframe>'

        with self.app.app_context():
            self.login_api_as(uid, roles=roles)
            self.assertEqual(expect, render(md))
