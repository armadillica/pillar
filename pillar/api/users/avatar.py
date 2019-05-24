import functools
import io
import logging
import mimetypes
import typing

from bson import ObjectId
from eve.methods.get import getitem_internal
import flask

from pillar import current_app
from pillar.api import blender_id
from pillar.api.blender_cloud import home_project
import pillar.api.file_storage
from werkzeug.datastructures import FileStorage

log = logging.getLogger(__name__)

DEFAULT_AVATAR = 'assets/img/default_user_avatar.png'


def url(user: dict) -> str:
    """Return the avatar URL for this user.

    :param user: dictionary from the MongoDB 'users' collection.
    """
    assert isinstance(user, dict), f'user must be dict, not {type(user)}'

    avatar_id = user.get('avatar', {}).get('file')
    if not avatar_id:
        return _default_avatar()

    # The file may not exist, in which case we get an empty string back.
    return pillar.api.file_storage.get_file_url(avatar_id) or _default_avatar()


@functools.lru_cache(maxsize=1)
def _default_avatar() -> str:
    """Return the URL path of the default avatar.

    Doesn't change after the app has started, so we just cache it.
    """
    return flask.url_for('static_pillar', filename=DEFAULT_AVATAR)


def _extension_for_mime(mime_type: str) -> str:
    # Take the longest extension. I'd rather have '.jpeg' than the weird '.jpe'.
    extensions: typing.List[str] = mimetypes.guess_all_extensions(mime_type)

    try:
        return max(extensions, key=len)
    except ValueError:
        # Raised when extensions is empty, e.g. when the mime type is unknown.
        return ''


def _get_file_link(file_id: ObjectId) -> str:
    # Get the file document via Eve to make it update the link.
    file_doc, _, _, status = getitem_internal('files', _id=file_id)
    assert status == 200

    return file_doc['link']


def sync_avatar(user_id: ObjectId) -> str:
    """Fetch the user's avatar from Blender ID and save to storage.

    Errors are logged but do not raise an exception.

    :return: the link to the avatar, or '' if it was not processed.
    """

    users_coll = current_app.db('users')
    db_user = users_coll.find_one({'_id': user_id})
    old_avatar_info = db_user.get('avatar', {})
    if isinstance(old_avatar_info, ObjectId):
        old_avatar_info = {'file': old_avatar_info}

    home_proj = home_project.get_home_project(user_id)
    if not home_project:
        log.error('Home project of user %s does not exist, unable to store avatar', user_id)
        return ''

    bid_userid = blender_id.get_user_blenderid(db_user)
    if not bid_userid:
        log.error('User %s has no Blender ID user-id, unable to fetch avatar', user_id)
        return ''

    avatar_url = blender_id.avatar_url(bid_userid)
    bid_session = blender_id.Session()

    # Avoid re-downloading the same avatar.
    request_headers = {}
    if avatar_url == old_avatar_info.get('last_downloaded_url') and \
            old_avatar_info.get('last_modified'):
        request_headers['If-Modified-Since'] = old_avatar_info.get('last_modified')

    log.info('Downloading avatar for user %s from %s', user_id, avatar_url)
    resp = bid_session.get(avatar_url, headers=request_headers, allow_redirects=True)
    if resp.status_code == 304:
        # File was not modified, we can keep the old file.
        log.debug('Avatar for user %s was not modified on Blender ID, not re-downloading', user_id)
        return _get_file_link(old_avatar_info['file'])

    resp.raise_for_status()

    mime_type = resp.headers['Content-Type']
    file_extension = _extension_for_mime(mime_type)
    if not file_extension:
        log.error('No file extension known for mime type %s, unable to handle avatar of user %s',
                  mime_type, user_id)
        return ''

    filename = f'avatar-{user_id}{file_extension}'
    fake_local_file = io.BytesIO(resp.content)
    fake_local_file.name = filename

    # Act as if this file was just uploaded by the user, so we can reuse
    # existing Pillar file-handling code.
    log.debug("Uploading avatar for user %s to storage", user_id)
    uploaded_file = FileStorage(
        stream=fake_local_file,
        filename=filename,
        headers=resp.headers,
        content_type=mime_type,
        content_length=resp.headers['Content-Length'],
    )

    with pillar.auth.temporary_user(db_user):
        upload_data = pillar.api.file_storage.upload_and_process(
            fake_local_file,
            uploaded_file,
            str(home_proj['_id']),
            # Disallow image processing, as it's a tiny file anyway and
            # we'll just serve the original.
            may_process_file=False,
        )
    file_id = ObjectId(upload_data['file_id'])

    avatar_info = {
        'file': file_id,
        'last_downloaded_url': resp.url,
        'last_modified': resp.headers.get('Last-Modified'),
    }

    # Update the user to store the reference to their avatar.
    old_avatar_file_id = old_avatar_info.get('file')
    update_result = users_coll.update_one({'_id': user_id},
                                          {'$set': {'avatar': avatar_info}})
    if update_result.matched_count == 1:
        log.debug('Updated avatar for user ID %s to file %s', user_id, file_id)
    else:
        log.warning('Matched %d users while setting avatar for user ID %s to file %s',
                    update_result.matched_count, user_id, file_id)

    if old_avatar_file_id:
        current_app.delete_internal('files', _id=old_avatar_file_id)

    return _get_file_link(file_id)
