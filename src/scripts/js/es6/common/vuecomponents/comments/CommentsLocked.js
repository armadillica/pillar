const TEMPLATE = `
<div class="comments-locked">
    <div
        v-if="msgToShow === 'PROJECT_MEMBERS_ONLY'"
    >
        <i class="pi-lock"/>
        Only project members can comment.
    </div>

    <div
        v-if="msgToShow === 'RENEW'"
    >
        <i class="pi-heart"/>
        Join the conversation!
        <a href="/renew" target="_blank"> Renew your subscription </a>
        to comment.
    </div>

    <div
        v-if="msgToShow === 'JOIN'"
    >
        <i class="pi-heart"/>
        Join the conversation!
        <a href="https://store.blender.org/product/membership/" target="_blank"> Subscribe to Blender Cloud </a>
        to comment.
    </div>

    <div
        v-if="msgToShow === 'LOGIN'"
    >
        <a href="/login"> Log in to comment</a>
    </div>
</div>
`;

Vue.component('comments-locked', {
    template: TEMPLATE,
    props: {user: Object},
    computed: {
        msgToShow() {
            if(this.user && this.user.is_authenticated) {
                if (this.user.hasCap('subscriber')) {
                    return 'PROJECT_MEMBERS_ONLY';
                } else if(this.user.hasCap('can-renew-subscription')) {
                    return 'RENEW';
                } else {
                    return 'JOIN';
                }
            }
            return 'LOGIN';
        }
    },
});