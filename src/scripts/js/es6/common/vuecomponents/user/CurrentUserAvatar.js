const TEMPLATE = `
<img class="user-avatar" :src="avatarUrl" alt="Your avatar">
`

export let CurrentUserAvatar = Vue.component("current-user-avatar", {
    data: function() { return {
        avatarUrl: "",
    }},
    template: TEMPLATE,
    created: function() {
        pillar.utils.currentUserEventBus.$on(pillar.utils.UserEvents.USER_LOADED, this.updateAvatarURL);
        this.updateAvatarURL(pillar.utils.getCurrentUser());
    },
    methods: {
        updateAvatarURL(user) {
            if (typeof user === 'undefined') {
                this.avatarUrl = '';
                return;
            }
            this.avatarUrl = user.avatar_url;
        },
    },
});
