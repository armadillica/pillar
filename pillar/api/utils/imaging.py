import json
import typing

import os
import pathlib
import subprocess

from PIL import Image
from flask import current_app

# Images with these modes will be thumbed to PNG, others to JPEG.
MODES_FOR_PNG = {'RGBA', 'LA'}


def generate_local_thumbnails(fp_base: str, src: pathlib.Path):
    """Given a source image, use Pillow to generate thumbnails according to the
    application settings.

    :param fp_base: the thumbnail will get a field
        'file_path': '{fp_base}-{thumbsize}.{ext}'
    :param src: the path of the image to be thumbnailed
    """

    thumbnail_settings = current_app.config['UPLOADS_LOCAL_STORAGE_THUMBNAILS']
    thumbnails = []

    for size, settings in thumbnail_settings.items():
        im = Image.open(src)
        extra_args = {}

        # If the source image has transparency, save as PNG
        if im.mode in MODES_FOR_PNG:
            suffix = '.png'
            imformat = 'PNG'
        else:
            suffix = '.jpg'
            imformat = 'JPEG'
            extra_args = {'quality': 95}
        dst = src.with_name(f'{src.stem}-{size}{suffix}')

        if settings['crop']:
            im = resize_and_crop(im, settings['size'])
        else:
            im.thumbnail(settings['size'], resample=Image.LANCZOS)
        width, height = im.size

        if imformat == 'JPEG':
            im = im.convert('RGB')
        im.save(dst, format=imformat, optimize=True, **extra_args)

        thumb_info = {'size': size,
                      'file_path': f'{fp_base}-{size}{suffix}',
                      'local_path': str(dst),
                      'length': dst.stat().st_size,
                      'width': width,
                      'height': height,
                      'md5': '',
                      'content_type': f'image/{imformat.lower()}'}

        if size == 't':
            thumb_info['is_public'] = True

        thumbnails.append(thumb_info)

    return thumbnails


def resize_and_crop(img: Image, size: typing.Tuple[int, int]) -> Image:
    """Resize and crop an image to fit the specified size.

    Thanks to: https://gist.github.com/sigilioso/2957026

    :param img: opened PIL.Image to work on
    :param size: `(width, height)` tuple.
    """
    # If height is higher we resize vertically, if not we resize horizontally
    # Get current and desired ratio for the images
    cur_w, cur_h = img.size  # current
    img_ratio = cur_w / cur_h

    w, h = size  # desired
    ratio = w / h

    # The image is scaled/cropped vertically or horizontally depending on the ratio
    if ratio > img_ratio:
        uncropped_h = (w * cur_h) // cur_w
        img = img.resize((w, uncropped_h), Image.ANTIALIAS)
        box = (0, (uncropped_h - h) // 2,
               w, (uncropped_h + h) // 2)
        img = img.crop(box)
    elif ratio < img_ratio:
        uncropped_w = (h * cur_w) // cur_h
        img = img.resize((uncropped_w, h), Image.ANTIALIAS)
        box = ((uncropped_w - w) // 2, 0,
               (uncropped_w + w) // 2, h)
        img = img.crop(box)
    else:
        img = img.resize((w, h), Image.ANTIALIAS)

    # If the scale is the same, we do not need to crop
    return img


def get_video_data(filepath):
    """Return video duration and resolution given an input file path"""
    outdata = None
    ffprobe_inspect = [
        current_app.config['BIN_FFPROBE'],
        '-loglevel',
        'error',
        '-show_streams',
        filepath,
        '-print_format',
        'json']

    ffprobe_ouput = json.loads(subprocess.check_output(ffprobe_inspect))

    video_stream = None
    # Loop throught audio and video streams searching for the video
    for stream in ffprobe_ouput['streams']:
        if stream['codec_type'] == 'video':
            video_stream = stream

    if video_stream:
        # If video is webm we can't get the duration (seems to be an ffprobe
        # issue)
        if video_stream['codec_name'] == 'vp8':
            duration = None
        else:
            duration = int(float(video_stream['duration']))
        outdata = dict(
            duration=duration,
            res_x=video_stream['width'],
            res_y=video_stream['height'],
        )
        if video_stream['sample_aspect_ratio'] != '1:1':
            print('[warning] Pixel aspect ratio is not square!')

    return outdata


def ffmpeg_encode(src, format, res_y=720):
    # The specific FFMpeg command, called multiple times
    args = []
    args.append("-i")
    args.append(src)

    if format == 'mp4':
        # Example mp4 encoding
        # ffmpeg -i INPUT -vcodec libx264 -pix_fmt yuv420p -preset fast -crf 20
        # -acodec libfdk_aac -ab 112k -ar 44100 -movflags +faststart OUTPUT
        args.extend([
            '-threads', '1',
            '-vf', 'scale=-2:{0}'.format(res_y),
            '-vcodec', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'fast',
            '-crf', '20',
            '-acodec', 'libfdk_aac', '-ab', '112k', '-ar', '44100',
            '-movflags', '+faststart'])
    elif format == 'webm':
        # Example webm encoding
        # ffmpeg -i INPUT -vcodec libvpx -g 120 -lag-in-frames 16 -deadline good
        # -cpu-used 0 -vprofile 0 -qmax 51 -qmin 11 -slices 4 -b:v 2M -f webm

        args.extend([
            '-vf', 'scale=-2:{0}'.format(res_y),
            '-vcodec', 'libvpx',
            '-g', '120',
            '-lag-in-frames', '16',
            '-deadline', 'good',
            '-cpu-used', '0',
            '-vprofile', '0',
            '-qmax', '51', '-qmin', '11', '-slices', '4', '-b:v', '2M',
            # '-acodec', 'libmp3lame', '-ab', '112k', '-ar', '44100',
            '-f', 'webm'])

    if not os.environ.get('VERBOSE'):
        args.extend(['-loglevel', 'quiet'])

    dst = os.path.splitext(src)
    dst = "{0}-{1}p.{2}".format(dst[0], res_y, format)
    args.append(dst)
    print("Encoding {0} to {1}".format(src, format))
    returncode = subprocess.call([current_app.config['BIN_FFMPEG']] + args)
    if returncode == 0:
        print("Successfully encoded {0}".format(dst))
    else:
        print("Error during encode")
        print("Code:    {0}".format(returncode))
        print("Command: {0}".format(current_app.config['BIN_FFMPEG'] + " " + " ".join(args)))
        dst = None
    # return path of the encoded video
    return dst
