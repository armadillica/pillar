from application import algolia_index_users

def algolia_index_user_save(user):
    # Define accepted roles
    accepted_roles = ['admin', 'subscriber', 'demo']
    # Strip unneeded roles
    if 'roles' in user:
        roles = [r for r in user['roles'] if r in accepted_roles]
    else:
        roles = None
    if algolia_index_users:
        # Create or update Algolia index for the user
        algolia_index_users.save_object({
            'objectID': user['_id'],
            'full_name': user['full_name'],
            'username': user['username'],
            'roles': roles,
            'groups': user['groups'],
            'email': user['email']
        })
