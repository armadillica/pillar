from eve.methods import get

import pillar.api.users.avatar


def for_node(node_id):
    activities, _, _, status, _ =\
        get('activities',
            {
                '$or': [
                    {'object_type': 'node',
                     'object': node_id},
                    {'context_object_type': 'node',
                     'context_object': node_id},
                ],
            },)

    for act in activities['_items']:
        act['actor_user'] = _user_info(act['actor_user'])

    return activities


def _user_info(user_id):
    users, _, _, status, _ = get('users', {'_id': user_id})
    if len(users['_items']) > 0:
        user = users['_items'][0]
        user['avatar'] = pillar.api.users.avatar.url(user)

        public_fields = {'full_name', 'username', 'avatar'}
        for field in list(user.keys()):
            if field not in public_fields:
                del user[field]

        return user
    return {}


def setup_app(app):
    global _user_info

    decorator = app.cache.memoize(timeout=300, make_name='%s.public_user_info' % __name__)
    _user_info = decorator(_user_info)
