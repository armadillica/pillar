class User{
    constructor(kwargs) {
        this.user_id = kwargs['user_id'] || '';
        this.username = kwargs['username'] || '';
        this.full_name = kwargs['full_name'] || '';
        this.gravatar = kwargs['gravatar'] || '';
        this.email = kwargs['email'] || '';
        this.capabilities = kwargs['capabilities'] || [];
        this.badges_html = kwargs['badges_html'] || '';
        this.is_authenticated = kwargs['is_authenticated'] || false;
    }

    /**
     * """Returns True iff the user has one or more of the given capabilities."""
     * @param  {...String} args 
     */
    hasCap(...args) {
        for(let cap of args) {
            if (this.capabilities.indexOf(cap) != -1) return true;
        }
        return false;
    }
}

let currentUser;
function initCurrentUser(kwargs){
    currentUser = new User(kwargs);
}

function getCurrentUser() {
    return currentUser;
}

export { getCurrentUser, initCurrentUser }