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
place it in [src/styles/font-pillar.sass](src/styles/font-pillar.sass).

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

## HDRi viewer

The HDRi viewer uses [Google VRView](https://github.com/googlevr/vrview). To upgrade,
get those files:

* [three.min.js](https://raw.githubusercontent.com/googlevr/vrview/master/build/three.min.js)
* [embed.min.js](https://raw.githubusercontent.com/googlevr/vrview/master/build/embed.min.js)
* [loading.gif](https://raw.githubusercontent.com/googlevr/vrview/master/images/loading.gif)

and place them in `pillar/web/static/assets/vrview`. Replace `images/loading.gif` in `embed.min.js` with `static/pillar/assets/vrview/loading.gif`.

You may also want to compare their
[index.html](https://raw.githubusercontent.com/googlevr/vrview/master/index.html) to our
`src/templates/vrview.jade`.

When on a HDRi page with the viewer embedded, use this JavaScript code to find the current
yaw: `vrview_window.contentWindow.yaw()`. This can be passed as `default_yaw` parameter to
the iframe.

## Celery

Pillar requires [Celery](http://www.celeryproject.org/) for background task processing. This in
turn requires a backend and a broker, for which the default Pillar configuration uses Redis and
RabbitMQ.

You can run the Celery Worker using `manage.py operations worker`.
