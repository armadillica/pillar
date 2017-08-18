import datetime
import io
import logging
import mimetypes
import os
import pathlib
import tempfile
import typing
import uuid
from hashlib import md5

import bson.tz_util
import eve.utils
import pymongo
import werkzeug.exceptions as wz_exceptions
import werkzeug.datastructures

from bson import ObjectId
from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request
from flask import send_from_directory
from flask import url_for, helpers

from pillar.api import utils
from pillar.api.file_storage_backends.gcs import GoogleCloudStorageBucket, \
    GoogleCloudStorageBlob
from pillar.api.utils import remove_private_keys, authentication
from pillar.api.utils.authorization import require_login, user_has_role, \
    user_matches_roles
from pillar.api.utils.cdn import hash_file_path
from pillar.api.utils.encoding import Encoder
from pillar.api.utils.imaging import generate_local_thumbnails
from pillar.api.file_storage_backends import default_storage_backend, Bucket

log = logging.getLogger(__name__)

file_storage = Blueprint('file_storage', __name__,
                         template_folder='templates',
                         static_folder='../../static/storage', )

# Overrides for browser-specified mimetypes
OVERRIDE_MIMETYPES = {
    # We don't want to thumbnail EXR files right now, so don't handle as image/...
    'image/x-exr': 'application/x-exr',
}
# Add our own extensions to the mimetypes package
mimetypes.add_type('application/x-blender', '.blend')
mimetypes.add_type('application/x-radiance-hdr', '.hdr')
mimetypes.add_type('application/x-exr', '.exr')


@file_storage.route('/file', methods=['POST'])
@file_storage.route('/file/<path:file_name>', methods=['GET', 'POST'])
def index(file_name=None):
    # GET file -> read it
    if request.method == 'GET':
        return send_from_directory(current_app.config['STORAGE_DIR'], file_name)

    # POST file -> save it

    # Sanitize the filename; source: http://stackoverflow.com/questions/7406102/
    file_name = request.form['name']
    keepcharacters = {' ', '.', '_'}
    file_name = ''.join(
        c for c in file_name if c.isalnum() or c in keepcharacters).strip()
    file_name = file_name.lstrip('.')

    # Determine & create storage directory
    folder_name = file_name[:2]
    file_folder_path = helpers.safe_join(current_app.config['STORAGE_DIR'],
                                         folder_name)
    if not os.path.exists(file_folder_path):
        log.info('Creating folder path %r', file_folder_path)
        os.mkdir(file_folder_path)

    # Save uploaded file
    file_path = helpers.safe_join(file_folder_path, file_name)
    log.info('Saving file %r', file_path)
    request.files['data'].save(file_path)

    # TODO: possibly nicer to just return a redirect to the file's URL.
    return jsonify({'url': url_for('file_storage.index', file_name=file_name)})


def _process_image(bucket: Bucket,
                   file_id: ObjectId,
                   local_file: tempfile._TemporaryFileWrapper,
                   src_file: dict):
    from PIL import Image

    im = Image.open(local_file)
    res = im.size
    src_file['width'] = res[0]
    src_file['height'] = res[1]

    # Generate previews
    log.info('Generating thumbnails for file %s', file_id)
    src_file['variations'] = generate_local_thumbnails(src_file['name'],
                                                       local_file.name)

    # Send those previews to Google Cloud Storage.
    log.info('Uploading %i thumbnails for file %s to Google Cloud Storage '
             '(GCS)', len(src_file['variations']), file_id)

    # TODO: parallelize this at some point.
    for variation in src_file['variations']:
        fname = variation['file_path']
        if current_app.config['TESTING']:
            log.warning('  - NOT sending thumbnail %s to %s', fname, bucket)
        else:
            blob = bucket.blob(fname)
            log.debug('  - Sending thumbnail %s to %s', fname, blob)
            blob.upload_from_path(pathlib.Path(variation['local_path']),
                                  content_type=variation['content_type'])

            if variation.get('size') == 't':
                blob.make_public()

        try:
            os.unlink(variation['local_path'])
        except OSError:
            log.warning('Unable to unlink %s, ignoring this but it will need '
                        'cleanup later.', variation['local_path'])

        del variation['local_path']

    log.info('Done processing file %s', file_id)
    src_file['status'] = 'complete'


def _video_size_pixels(filename: pathlib.Path) -> typing.Tuple[int, int]:
    """Figures out the size (in pixels) of the video file.

    Returns (0, 0) if there was any error detecting the size.
    """

    import json
    import subprocess

    cli_args = [
        current_app.config['BIN_FFPROBE'],
        '-loglevel', 'error',
        '-hide_banner',
        '-print_format', 'json',
        '-select_streams', 'v:0',  # we only care about the first video stream
        '-show_streams',
        str(filename),
    ]

    if log.isEnabledFor(logging.INFO):
        import shlex
        cmd = ' '.join(shlex.quote(s) for s in cli_args)
        log.info('Calling %s', cmd)

    ffprobe = subprocess.run(
        cli_args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,  # seconds
    )

    if ffprobe.returncode:
        import shlex
        cmd = ' '.join(shlex.quote(s) for s in cli_args)
        log.error('Error running %s: stopped with return code %i',
                  cmd, ffprobe.returncode)
        log.error('Output was: %s', ffprobe.stdout)
        return 0, 0

    try:
        ffprobe_info = json.loads(ffprobe.stdout)
    except json.JSONDecodeError:
        log.exception('ffprobe produced invalid JSON: %s', ffprobe.stdout)
        return 0, 0

    try:
        stream_info = ffprobe_info['streams'][0]
        return stream_info['width'], stream_info['height']
    except (KeyError, IndexError):
        log.exception('ffprobe produced unexpected JSON: %s', ffprobe.stdout)
        return 0, 0


def _video_cap_at_1080(width: int, height: int) -> typing.Tuple[int, int]:
    """Returns an appropriate width/height for a video capped at 1920x1080.

    Takes into account that h264 has limitations:
        - the width must be a multiple of 16
        - the height must be a multiple of 8
    """

    if width > 1920:
        # The height must be a multiple of 8
        new_height = height / width * 1920
        height = new_height - (new_height % 8)
        width = 1920

    if height > 1080:
        # The width must be a multiple of 16
        new_width = width / height * 1080
        width = new_width - (new_width % 16)
        height = 1080

    return int(width), int(height)


def _process_video(gcs,
                   file_id: ObjectId,
                   local_file: tempfile._TemporaryFileWrapper,
                   src_file: dict):
    """Video is processed by Zencoder."""

    log.info('Processing video for file %s', file_id)

    # Use ffprobe to find the size (in pixels) of the video.
    # Even though Zencoder can do resizing to a maximum resolution without upscaling,
    # by determining the video size here we already have this information in the file
    # document before Zencoder calls our notification URL. It also opens up possibilities
    # for other encoding backends that don't support this functionality.
    video_width, video_height = _video_size_pixels(pathlib.Path(local_file.name))
    capped_video_width, capped_video_height = _video_cap_at_1080(video_width, video_height)

    # Create variations
    root, _ = os.path.splitext(src_file['file_path'])
    src_file['variations'] = []

    # Most of these properties will be available after encode.
    v = 'mp4'
    file_variation = dict(
        format=v,
        content_type='video/{}'.format(v),
        file_path='{}-{}.{}'.format(root, v, v),
        size='',
        duration=0,
        width=capped_video_width,
        height=capped_video_height,
        length=0,
        md5='',
    )
    # Append file variation. Originally mp4 and webm were the available options,
    # that's why we build a list.
    src_file['variations'].append(file_variation)

    if current_app.config['TESTING']:
        log.warning('_process_video: NOT sending out encoding job due to '
                    'TESTING=%r', current_app.config['TESTING'])
        j = {'process_id': 'fake-process-id',
             'backend': 'fake'}
    else:
        j = Encoder.job_create(src_file)
        if j is None:
            log.warning('_process_video: unable to create encoder job for file '
                        '%s.', file_id)
            return

    log.info('Created asynchronous Zencoder job %s for file %s',
             j['process_id'], file_id)

    # Add the processing status to the file object
    src_file['processing'] = {
        'status': 'pending',
        'job_id': str(j['process_id']),
        'backend': j['backend']}


def process_file(bucket: Bucket,
                 file_id: typing.Union[str, ObjectId],
                 local_file: tempfile._TemporaryFileWrapper):
    """Process the file by creating thumbnails, sending to Zencoder, etc.

    :param file_id: '_id' key of the file
    :param local_file: locally stored file, or None if no local processing is
    needed.
    """

    file_id = ObjectId(file_id)

    # Fetch the src_file document from MongoDB.
    files = current_app.data.driver.db['files']
    src_file = files.find_one(file_id)
    if not src_file:
        log.warning('process_file(%s): no such file document found, ignoring.')
        return
    src_file = utils.remove_private_keys(src_file)

    # Update the 'format' field from the content type.
    # TODO: overrule the content type based on file extention & magic numbers.
    mime_category, src_file['format'] = src_file['content_type'].split('/', 1)

    # Prevent video handling for non-admins.
    if not user_has_role('admin') and mime_category == 'video':
        if src_file['format'].startswith('x-'):
            xified = src_file['format']
        else:
            xified = 'x-' + src_file['format']

        src_file['content_type'] = 'application/%s' % xified
        mime_category = 'application'
        log.info('Not processing video file %s for non-admin user', file_id)

    # Run the required processor, based on the MIME category.
    processors: typing.Mapping[str, typing.Callable] = {
        'image': _process_image,
        'video': _process_video,
    }

    try:
        processor = processors[mime_category]
    except KeyError:
        log.info("POSTed file %s was of type %r, which isn't "
                 "thumbnailed/encoded.", file_id,
                 mime_category)
        src_file['status'] = 'complete'
    else:
        log.debug('process_file(%s): marking file status as "processing"',
                  file_id)
        src_file['status'] = 'processing'
        update_file_doc(file_id, status='processing')

        try:
            processor(bucket, file_id, local_file, src_file)
        except Exception:
            log.warning('process_file(%s): error when processing file, '
                        'resetting status to '
                        '"queued_for_processing"', file_id, exc_info=True)
            update_file_doc(file_id, status='queued_for_processing')
            return

    # Update the original file with additional info, e.g. image resolution
    r, _, _, status = current_app.put_internal('files', src_file, _id=file_id)
    if status not in (200, 201):
        log.warning('process_file(%s): status %i when saving processed file '
                    'info to MongoDB: %s',
                    file_id, status, r)


def generate_link(backend, file_path: str, project_id=None, is_public=False) -> str:
    """Hook to check the backend of a file resource, to build an appropriate link
    that can be used by the client to retrieve the actual file.
    """

    # TODO: replace config['TESTING'] with mocking GCS.
    if backend == 'gcs' and current_app.config['TESTING']:
        log.info('Skipping GCS link generation, and returning a fake link '
                 'instead.')
        return '/path/to/testing/gcs/%s' % file_path

    if backend in {'gcs', 'local'}:
        from ..file_storage_backends import Bucket

        bucket_cls = Bucket.for_backend(backend)
        storage = bucket_cls(project_id)
        blob = storage.get_blob(file_path)

        if blob is None:
            log.warning('generate_link(%r, %r): unable to find blob for file'
                        ' path, returning empty link.', backend, file_path)
            return ''

        return blob.get_url(is_public=is_public)

    if backend == 'pillar':
        return url_for('file_storage.index', file_name=file_path,
                       _external=True, _scheme=current_app.config['SCHEME'])
    if backend == 'cdnsun':
        return hash_file_path(file_path, None)
    if backend == 'unittest':
        return 'https://unit.test/%s' % md5(file_path.encode()).hexdigest()

    log.warning('generate_link(): Unknown backend %r, returning empty string '
                'as new link.',
                backend)
    return ''


def before_returning_file(response):
    ensure_valid_link(response)

    # Enable this call later, when we have implemented the is_public field on
    # files.
    # strip_link_and_variations(response)


def strip_link_and_variations(response):
    # Check the access level of the user.
    if g.current_user is None:
        has_full_access = False
    else:
        user_roles = g.current_user['roles']
        access_roles = current_app.config['FULL_FILE_ACCESS_ROLES']
        has_full_access = bool(user_roles.intersection(access_roles))

    # Strip all file variations (unless image) and link to the actual file.
    if not has_full_access:
        response.pop('link', None)
        response.pop('link_expires', None)

        # Image files have public variations, other files don't.
        if not response.get('content_type', '').startswith('image/'):
            if response.get('variations') is not None:
                response['variations'] = []


def before_returning_files(response):
    for item in response['_items']:
        ensure_valid_link(item)


def ensure_valid_link(response):
    """Ensures the file item has valid file links using generate_link(...)."""

    # Log to function-specific logger, so we can easily turn it off.
    log_link = logging.getLogger('%s.ensure_valid_link' % __name__)
    # log.debug('Inspecting link for file %s', response['_id'])

    # Check link expiry.
    now = datetime.datetime.now(tz=bson.tz_util.utc)
    if 'link_expires' in response:
        link_expires = response['link_expires']
        if now < link_expires:
            # Not expired yet, so don't bother regenerating anything.
            log_link.debug('Link expires at %s, which is in the future, so not '
                           'generating new link', link_expires)
            return

        log_link.debug('Link expired at %s, which is in the past; generating '
                       'new link', link_expires)
    else:
        log_link.debug('No expiry date for link; generating new link')

    generate_all_links(response, now)


def generate_all_links(response, now):
    """Generate a new link for the file and all its variations.

    :param response: the file document that should be updated.
    :param now: datetime that reflects 'now', for consistent expiry generation.
    """

    project_id = str(
        response['project']) if 'project' in response else None
    # TODO: add project id to all files
    backend = response['backend']
    response['link'] = generate_link(backend, response['file_path'], project_id)

    variations = response.get('variations')
    if variations:
        for variation in variations:
            variation['link'] = generate_link(backend, variation['file_path'],
                                              project_id)

    # Construct the new expiry datetime.
    validity_secs = current_app.config['FILE_LINK_VALIDITY'][backend]
    response['link_expires'] = now + datetime.timedelta(seconds=validity_secs)

    patch_info = remove_private_keys(response)
    file_id = ObjectId(response['_id'])
    (patch_resp, _, _, _) = current_app.patch_internal('files', patch_info,
                                                       _id=file_id)
    if patch_resp.get('_status') == 'ERR':
        log.warning('Unable to save new links for file %s: %r',
                    response['_id'], patch_resp)
        # TODO: raise a snag.
        response['_updated'] = now
    else:
        response['_updated'] = patch_resp['_updated']

    # Be silly and re-fetch the etag ourselves. TODO: handle this better.
    etag_doc = current_app.data.driver.db['files'].find_one({'_id': file_id},
                                                            {'_etag': 1})
    response['_etag'] = etag_doc['_etag']


def on_pre_get_files(_, lookup):
    # Override the HTTP header, we always want to fetch the document from
    # MongoDB.
    parsed_req = eve.utils.parse_request('files')
    parsed_req.if_modified_since = None

    # Only fetch it if the date got expired.
    now = datetime.datetime.now(tz=bson.tz_util.utc)
    lookup_expired = lookup.copy()
    lookup_expired['link_expires'] = {'$lte': now}

    cursor = current_app.data.find('files', parsed_req, lookup_expired)
    for file_doc in cursor:
        # log.debug('Updating expired links for file %r.', file_doc['_id'])
        generate_all_links(file_doc, now)


def refresh_links_for_project(project_uuid, chunk_size, expiry_seconds):
    if chunk_size:
        log.info('Refreshing the first %i links for project %s',
                 chunk_size, project_uuid)
    else:
        log.info('Refreshing all links for project %s', project_uuid)

    # Retrieve expired links.
    files_collection = current_app.data.driver.db['files']

    now = datetime.datetime.now(tz=bson.tz_util.utc)
    expire_before = now + datetime.timedelta(seconds=expiry_seconds)
    log.info('Limiting to links that expire before %s', expire_before)

    to_refresh = files_collection.find(
        {'project': ObjectId(project_uuid),
         'link_expires': {'$lt': expire_before},
         }).sort([('link_expires', pymongo.ASCENDING)]).limit(chunk_size)

    if to_refresh.count() == 0:
        log.info('No links to refresh.')
        return

    for file_doc in to_refresh:
        log.debug('Refreshing links for file %s', file_doc['_id'])
        generate_all_links(file_doc, now)

    log.info('Refreshed %i links', min(chunk_size, to_refresh.count()))


def refresh_links_for_backend(backend_name, chunk_size, expiry_seconds):
    import gcloud.exceptions

    # Retrieve expired links.
    files_collection = current_app.data.driver.db['files']
    proj_coll = current_app.data.driver.db['projects']

    now = datetime.datetime.now(tz=bson.tz_util.utc)
    expire_before = now + datetime.timedelta(seconds=expiry_seconds)
    log.info('Limiting to links that expire before %s', expire_before)

    to_refresh = files_collection.find(
        {'$or': [{'backend': backend_name, 'link_expires': None},
                 {'backend': backend_name, 'link_expires': {
                     '$lt': expire_before}},
                 {'backend': backend_name, 'link': None}]
         }).sort([('link_expires', pymongo.ASCENDING)]).limit(
        chunk_size).batch_size(5)

    if to_refresh.count() == 0:
        log.info('No links to refresh.')
        return

    refreshed = 0
    for file_doc in to_refresh:
        try:
            file_id = file_doc['_id']
            project_id = file_doc.get('project')
            if project_id is None:
                log.debug('Skipping file %s, it has no project.', file_id)
                continue

            count = proj_coll.count({'_id': project_id, '$or': [
                {'_deleted': {'$exists': False}},
                {'_deleted': False},
            ]})

            if count == 0:
                log.debug('Skipping file %s, project %s does not exist.',
                          file_id, project_id)
                continue

            if 'file_path' not in file_doc:
                log.warning("Skipping file %s, missing 'file_path' property.",
                            file_id)
                continue

            log.debug('Refreshing links for file %s', file_id)

            try:
                generate_all_links(file_doc, now)
            except gcloud.exceptions.Forbidden:
                log.warning('Skipping file %s, GCS forbids us access to '
                            'project %s bucket.', file_id, project_id)
                continue
            refreshed += 1
        except KeyboardInterrupt:
            log.warning('Aborting due to KeyboardInterrupt after refreshing %i '
                        'links', refreshed)
            return

    log.info('Refreshed %i links', refreshed)


@require_login()
def create_file_doc(name, filename, content_type, length, project,
                    backend=None, **extra_fields):
    """Creates a minimal File document for storage in MongoDB.

    Doesn't save it to MongoDB yet.
    """

    if backend is None:
        backend = current_app.config['STORAGE_BACKEND']

    current_user = g.get('current_user')

    file_doc = {'name': name,
                'filename': filename,
                'file_path': '',
                'user': current_user['user_id'],
                'backend': backend,
                'md5': '',
                'content_type': content_type,
                'length': length,
                'project': project}
    file_doc.update(extra_fields)

    return file_doc


def override_content_type(uploaded_file):
    """Overrides the content type based on file extensions.

    :param uploaded_file: file from request.files['form-key']
    :type uploaded_file: werkzeug.datastructures.FileStorage
    """

    # Possibly use the browser-provided mime type
    mimetype = uploaded_file.mimetype

    try:
        mimetype = OVERRIDE_MIMETYPES[mimetype]
    except KeyError:
        pass

    if '/' in mimetype:
        mimecat = mimetype.split('/')[0]
        if mimecat in {'video', 'audio', 'image'}:
            # The browser's mime type is probably ok, just use it.
            return

    # And then use it to set the mime type.
    (mimetype, encoding) = mimetypes.guess_type(uploaded_file.filename)

    # Only override the mime type if we can detect it, otherwise just
    # keep whatever the browser gave us.
    if mimetype:
        # content_type property can't be set directly
        uploaded_file.headers['content-type'] = mimetype

        # It has this, because we used uploaded_file.mimetype earlier this
        # function.
        del uploaded_file._parsed_content_type


def assert_file_size_allowed(file_size: int):
    """Asserts that the current user is allowed to upload a file of the given size.

    :raises wz_exceptions.RequestEntityTooLarge:
    """

    roles = current_app.config['ROLES_FOR_UNLIMITED_UPLOADS']
    if user_matches_roles(require_roles=roles):
        return

    filesize_limit = current_app.config['FILESIZE_LIMIT_BYTES_NONSUBS']
    if file_size < filesize_limit:
        return

    filesize_limit_mb = filesize_limit / 2.0 ** 20
    log.info('User %s tried to upload a %.3f MiB file, but is only allowed '
             '%.3f MiB.',
             authentication.current_user_id(), file_size / 2.0 ** 20,
             filesize_limit_mb)
    raise wz_exceptions.RequestEntityTooLarge(
        'To upload files larger than %i MiB, subscribe to Blender Cloud' %
        filesize_limit_mb)


@file_storage.route('/stream/<string:project_id>', methods=['POST', 'OPTIONS'])
@require_login()
def stream_to_storage(project_id: str):
    project_oid = utils.str2id(project_id)

    projects = current_app.data.driver.db['projects']
    project = projects.find_one(project_oid, projection={'_id': 1})

    if not project:
        raise wz_exceptions.NotFound('Project %s does not exist' % project_id)

    log.info('Streaming file to bucket for project=%s user_id=%s', project_id,
             authentication.current_user_id())
    log.info('request.headers[Origin] = %r', request.headers.get('Origin'))
    log.info('request.content_length = %r', request.content_length)

    # Try a check for the content length before we access request.files[].
    # This allows us to abort the upload early. The entire body content length
    # is always a bit larger than the actual file size, so if we accept here,
    # we're sure it'll be accepted in subsequent checks as well.
    if request.content_length:
        assert_file_size_allowed(request.content_length)

    uploaded_file = request.files['file']

    # Not every upload has a Content-Length header. If it was passed, we might
    # as well check for its value before we require the user to upload the
    # entire file. (At least I hope that this part of the code is processed
    # before the body is read in its entirety)
    if uploaded_file.content_length:
        assert_file_size_allowed(uploaded_file.content_length)

    override_content_type(uploaded_file)
    if not uploaded_file.content_type:
        log.warning('File uploaded to project %s without content type.',
                    project_oid)
        raise wz_exceptions.BadRequest('Missing content type.')

    if uploaded_file.content_type.startswith('image/') or uploaded_file.content_type.startswith(
            'video/'):
        # We need to do local thumbnailing and ffprobe, so we have to write the stream
        # both to Google Cloud Storage and to local storage.
        local_file = tempfile.NamedTemporaryFile(
            dir=current_app.config['STORAGE_DIR'])
        uploaded_file.save(local_file)
        local_file.seek(0)  # Make sure that re-read starts from the beginning.
    else:
        local_file = uploaded_file.stream

    result = upload_and_process(local_file, uploaded_file, project_id)
    resp = jsonify(result)
    resp.status_code = result['status_code']
    add_access_control_headers(resp)
    return resp


def upload_and_process(local_file: typing.Union[io.BytesIO, typing.BinaryIO],
                       uploaded_file: werkzeug.datastructures.FileStorage,
                       project_id: str):
    # Figure out the file size, as we need to pass this in explicitly to GCloud.
    # Otherwise it always uses os.fstat(file_obj.fileno()).st_size, which isn't
    # supported by a BytesIO object (even though it does have a fileno
    # attribute).
    if isinstance(local_file, io.BytesIO):
        file_size = len(local_file.getvalue())
    else:
        file_size = os.fstat(local_file.fileno()).st_size

    # Check the file size again, now that we know its size for sure.
    assert_file_size_allowed(file_size)

    # Create file document in MongoDB.
    file_id, internal_fname, status = create_file_doc_for_upload(project_id, uploaded_file)

    # Copy the file into storage.
    bucket = default_storage_backend(project_id)
    blob = bucket.blob(internal_fname)
    blob.create_from_file(local_file,
                          file_size=file_size,
                          content_type=uploaded_file.mimetype)

    log.debug('Marking uploaded file id=%s, fname=%s, '
              'size=%i as "queued_for_processing"',
              file_id, internal_fname, file_size)
    update_file_doc(file_id,
                    status='queued_for_processing',
                    file_path=internal_fname,
                    length=blob.size,
                    content_type=uploaded_file.mimetype)

    log.debug('Processing uploaded file id=%s, fname=%s, size=%i', file_id,
              internal_fname, blob.size)
    process_file(bucket, file_id, local_file)

    # Local processing is done, we can close the local file so it is removed.
    if local_file is not None:
        local_file.close()

    log.debug('Handled uploaded file id=%s, fname=%s, size=%i, status=%i',
              file_id, internal_fname, blob.size, status)

    # Status is 200 if the file already existed, and 201 if it was newly
    # created.
    # TODO: add a link to a thumbnail in the response.
    return dict(status='ok', file_id=str(file_id), status_code=status)


from ..file_storage_backends.abstract import FileType


def stream_to_gcs(file_id: ObjectId, file_size: int, internal_fname: str, project_id: ObjectId,
                  stream_for_gcs: FileType, content_type: str) \
        -> typing.Tuple[GoogleCloudStorageBlob, GoogleCloudStorageBucket]:
    # Upload the file to GCS.
    try:
        bucket = GoogleCloudStorageBucket(str(project_id))
        blob = bucket.blob(internal_fname)
        blob.create_from_file(stream_for_gcs, file_size=file_size, content_type=content_type)
    except Exception:
        log.exception('Error uploading file to Google Cloud Storage (GCS),'
                      ' aborting handling of uploaded file (id=%s).', file_id)
        update_file_doc(file_id, status='failed')
        raise wz_exceptions.InternalServerError(
            'Unable to stream file to Google Cloud Storage')

    return blob, bucket


def add_access_control_headers(resp):
    """Allows cross-site requests from the configured domain."""

    if 'Origin' not in request.headers:
        return resp

    resp.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return resp


def create_file_doc_for_upload(project_id, uploaded_file):
    """Creates a secure filename and a document in MongoDB for the file.

    The (project_id, filename) tuple should be unique. If such a document already
    exists, it is updated with the new file.

    :param uploaded_file: file from request.files['form-key']
    :type uploaded_file: werkzeug.datastructures.FileStorage
    :returns: a tuple (file_id, filename, status), where 'filename' is the internal
            filename used on GCS.
    """

    project_id = ObjectId(project_id)

    # Hash the filename with path info to get the internal name. This should
    # be unique for the project.
    # internal_filename = uploaded_file.filename
    _, ext = os.path.splitext(uploaded_file.filename)
    internal_filename = uuid.uuid4().hex + ext

    # For now, we don't support overwriting files, and create a new one every time.
    # # See if we can find a pre-existing file doc.
    # files = current_app.data.driver.db['files']
    # file_doc = files.find_one({'project': project_id,
    #                            'name': internal_filename})
    file_doc = None

    # TODO: at some point do name-based and content-based content-type sniffing.
    new_props = {'filename': uploaded_file.filename,
                 'content_type': uploaded_file.mimetype,
                 'length': uploaded_file.content_length,
                 'project': project_id,
                 'status': 'uploading'}

    if file_doc is None:
        # Create a file document on MongoDB for this file.
        file_doc = create_file_doc(name=internal_filename, **new_props)
        file_fields, _, _, status = current_app.post_internal('files', file_doc)
    else:
        file_doc.update(new_props)
        file_fields, _, _, status = current_app.put_internal('files', remove_private_keys(file_doc))

    if status not in (200, 201):
        log.error('Unable to create new file document in MongoDB, status=%i: %s',
                  status, file_fields)
        raise wz_exceptions.InternalServerError()

    log.debug('Created file document %s for uploaded file %s; internal name %s',
              file_fields['_id'], uploaded_file.filename, internal_filename)

    return file_fields['_id'], internal_filename, status


def compute_aggregate_length(file_doc, original=None):
    """Computes the total length (in bytes) of the file and all variations.

    Stores the result in file_doc['length_aggregate_in_bytes']
    """

    # Compute total size of all variations.
    variations = file_doc.get('variations', ())
    var_length = sum(var.get('length', 0) for var in variations)

    file_doc['length_aggregate_in_bytes'] = file_doc.get('length', 0) + var_length


def compute_aggregate_length_items(file_docs):
    for file_doc in file_docs:
        compute_aggregate_length(file_doc)


def setup_app(app, url_prefix):
    app.on_pre_GET_files += on_pre_get_files

    app.on_fetched_item_files += before_returning_file
    app.on_fetched_resource_files += before_returning_files

    app.on_update_files += compute_aggregate_length
    app.on_replace_files += compute_aggregate_length
    app.on_insert_files += compute_aggregate_length_items

    app.register_api_blueprint(file_storage, url_prefix=url_prefix)


def update_file_doc(file_id, **updates):
    files = current_app.data.driver.db['files']
    res = files.update_one({'_id': ObjectId(file_id)},
                           {'$set': updates})
    log.debug('update_file_doc(%s, %s): %i matched, %i updated.',
              file_id, updates, res.matched_count, res.modified_count)
    return res
