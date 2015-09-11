import os
from PIL import Image
from application import app


def generate_local_thumbnails(src, return_image_stats=False):
    """Given a source image, use Pillow to generate thumbnails according to the
    application settings.

    args:
    src: the path of the image to be thumbnailed
    return_image_stats: if True, return a dict object which contains length,
    resolution, format and path of the thumbnailed image
    """

    thumbnail_settings = app.config['UPLOADS_LOCAL_STORAGE_THUMBNAILS']
    thumbnails = {}
    for size, settings in thumbnail_settings.iteritems():
        root, ext = os.path.splitext(src)
        dst = "{0}-{1}{2}".format(root, size, '.jpg')
        if os.path.isfile(dst):
            # If the thumbnail already exists we require stats about it
            if return_image_stats:
                thumbnails[size] = dict(exists=True)
            continue
        if settings['crop']:
            resize_and_crop(src, dst, settings['size'])
        else:
            im = Image.open(src)
            im.thumbnail(settings['size'])
            im.save(dst, "JPEG")

        if return_image_stats:
            # Get file size
            st = os.stat(dst)
            length = st.st_size
            # Get resolution
            im = Image.open(dst)
            width = im.size[0]
            height = im.size[1]
            format = im.format.lower()
            # Get format
            thumbnails[size] = dict(
                path=dst, # Full path, to be processed before storage
                length=length,
                width=width,
                height=height,
                md5='--',
                content_type='image/' + format,
                )

    if return_image_stats:
        return thumbnails


def resize_and_crop(img_path, modified_path, size, crop_type='middle'):
    """
    Resize and crop an image to fit the specified size. Thanks to:
    https://gist.github.com/sigilioso/2957026

    args:
    img_path: path for the image to resize.
    modified_path: path to store the modified image.
    size: `(width, height)` tuple.
    crop_type: can be 'top', 'middle' or 'bottom', depending on this
    value, the image will cropped getting the 'top/left', 'middle' or
    'bottom/right' of the image to fit the size.
    raises:
    Exception: if can not open the file in img_path of there is problems
    to save the image.
    ValueError: if an invalid `crop_type` is provided.

    """
    # If height is higher we resize vertically, if not we resize horizontally
    img = Image.open(img_path)
    # Get current and desired ratio for the images
    img_ratio = img.size[0] / float(img.size[1])
    ratio = size[0] / float(size[1])
    #The image is scaled/cropped vertically or horizontally depending on the ratio
    if ratio > img_ratio:
        img = img.resize((size[0], int(round(size[0] * img.size[1] / img.size[0]))),
            Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, img.size[0], size[1])
        elif crop_type == 'middle':
            box = (0, int(round((img.size[1] - size[1]) / 2)), img.size[0],
                int(round((img.size[1] + size[1]) / 2)))
        elif crop_type == 'bottom':
            box = (0, img.size[1] - size[1], img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    elif ratio < img_ratio:
        img = img.resize((int(round(size[1] * img.size[0] / img.size[1])), size[1]),
            Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, size[0], img.size[1])
        elif crop_type == 'middle':
            box = (int(round((img.size[0] - size[0]) / 2)), 0,
                int(round((img.size[0] + size[0]) / 2)), img.size[1])
        elif crop_type == 'bottom':
            box = (img.size[0] - size[0], 0, img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    else :
        img = img.resize((size[0], size[1]),
            Image.ANTIALIAS)
    # If the scale is the same, we do not need to crop
    img.save(modified_path, "JPEG")
