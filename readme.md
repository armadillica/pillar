Pillar
======

This is the latest iteration on the Attract project. We are building a unified
framework called Pillar. Pillar will combine Blender Cloud and Attract. You
can see Pillar in action on the [Blender Cloud](https://cloud.bender.org).

## Custom fonts

The icons on the website are drawn using a custom font, stored in
[pillar/web/static/font](pillar/web/static/font).
This font is generated via [Fontello](http://fontello.com/) by uploading
[pillar/web/static/font/config.json](pillar/web/static/font/config.json).

Note that we only use the WOFF and WOFF2 formats, and discard the others
supplied by Fontello.

After replacing the font files & `config.json`, edit the Fontello-supplied
`font.css` to remove all font formats except `woff` and `woff2`. Then upload
it to [css2sass](http://css2sass.herokuapp.com/) to convert it to SASS, and
place it in [src/styles/_font-pillar.sass](src/styles/_font-pillar.sass).

Don't forget to Gulp!


## Installation

Make sure your /data directory exists and is writable by the current user.
Alternatively, provide a `pillar/config_local.py` that changes the relevant
settings.

```
git clone git@git.blender.org:pillar-python-sdk.git ../pillar-python-sdk
pip install -e ../pillar-python-sdk
pip install -U -r requirements.txt
pip install -e .
```
