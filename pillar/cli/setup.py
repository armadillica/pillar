import logging

from flask_script import Manager

from pillar import current_app

log = logging.getLogger(__name__)

manager_setup = Manager(
    current_app, usage="Setup utilities, like setup_db() or create_blog()")


@manager_setup.command
def setup_db(admin_email):
    """Setup the database
    - Create admin, subscriber and demo Group collection
    - Create admin user (must use valid blender-id credentials)
    - Create one project
    """

    # Create default groups
    groups_list = []
    for group in ['admin', 'subscriber', 'demo']:
        g = {'name': group}
        g = current_app.post_internal('groups', g)
        groups_list.append(g[0]['_id'])
        print("Creating group {0}".format(group))

    # Create admin user
    user = {'username': admin_email,
            'groups': groups_list,
            'roles': ['admin', 'subscriber', 'demo'],
            'settings': {'email_communications': 1},
            'auth': [],
            'full_name': admin_email,
            'email': admin_email}
    result, _, _, status = current_app.post_internal('users', user)
    if status != 201:
        raise SystemExit('Error creating user {}: {}'.format(admin_email, result))
    user.update(result)
    print("Created user {0}".format(user['_id']))

    # Create a default project by faking a POST request.
    with current_app.test_request_context(data={'project_name': 'Default Project'}):
        from flask import g
        from pillar.api.projects import routes as proj_routes

        g.current_user = {'user_id': user['_id'],
                          'groups': user['groups'],
                          'roles': set(user['roles'])}

        proj_routes.create_project(overrides={'url': 'default-project',
                                              'is_private': False})


@manager_setup.command
def create_badger_account(email, badges):
    """
    Creates a new service account that can give badges (i.e. roles).

    :param email: email address associated with the account
    :param badges: single space-separated argument containing the roles
        this account can assign and revoke.
    """

    create_service_account(email, ['badger'], {'badger': badges.strip().split()})


@manager_setup.command
def create_urler_account(email):
    """Creates a new service account that can fetch all project URLs."""

    create_service_account(email, ['urler'], {})


@manager_setup.command
def create_local_user_account(email, password):
    from pillar.api.local_auth import create_local_user
    create_local_user(email, password)


@manager_setup.command
def badger(action, user_email, role):
    from pillar.api import service

    with current_app.app_context():
        service.fetch_role_to_group_id_map()
        response, status = service.do_badger(action, role=role, user_email=user_email)

    if status == 204:
        log.info('Done.')
    else:
        log.info('Response: %s', response)
        log.info('Status  : %i', status)


@manager_setup.command
def create_blog(proj_url):
    """Adds a blog to the project."""

    from pillar.api.utils.authentication import force_cli_user
    from pillar.api.utils import node_type_utils
    from pillar.api.node_types.blog import node_type_blog
    from pillar.api.node_types.post import node_type_post
    from pillar.api.utils import remove_private_keys

    force_cli_user()

    db = current_app.db()

    # Add the blog & post node types to the project.
    projects_coll = db['projects']
    proj = projects_coll.find_one({'url': proj_url})
    if not proj:
        log.error('Project url=%s not found', proj_url)
        return 3

    node_type_utils.add_to_project(proj,
                                   (node_type_blog, node_type_post),
                                   replace_existing=False)

    proj_id = proj['_id']
    r, _, _, status = current_app.put_internal('projects', remove_private_keys(proj), _id=proj_id)
    if status != 200:
        log.error('Error %i storing altered project %s %s', status, proj_id, r)
        return 4
    log.info('Project saved succesfully.')

    # Create a blog node.
    nodes_coll = db['nodes']
    blog = nodes_coll.find_one({'node_type': 'blog', 'project': proj_id})
    if not blog:
        blog = {
            'node_type': node_type_blog['name'],
            'name': 'Blog',
            'description': '',
            'properties': {},
            'project': proj_id,
        }
        r, _, _, status = current_app.post_internal('nodes', blog)
        if status != 201:
            log.error('Error %i storing blog node: %s', status, r)
            return 4
        log.info('Blog node saved succesfully: %s', r)
    else:
        log.info('Blog node already exists: %s', blog)

    return 0


def create_service_account(email, service_roles, service_definition,
                           *, full_name: str=None):
    from pillar.api import service
    from pillar.api.utils import dumps

    account, token = service.create_service_account(
        email,
        service_roles,
        service_definition,
        full_name=full_name,
    )

    print('Service account information:')
    print(dumps(account, indent=4, sort_keys=True))
    print()
    print('Access token: %s' % token['token'])
    print('  expires on: %s' % token['expire_time'])
    return account, token
