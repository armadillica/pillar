// The <i> is given a fixed width so that the button doesn't resize when we change the icon.
const TEMPLATE = `
<button class="btn btn-outline-primary" type="button" @click="syncAvatar"
        :disabled="isSyncing">
    <i style="width: 2em; display: inline-block"
        :class="{'pi-refresh': !isSyncing, 'pi-spin': isSyncing, spin: isSyncing}"></i>
    Fetch Avatar from Blender ID
</button>
`

Vue.component("avatar-sync-button", {
    template: TEMPLATE,
    data() { return {
        isSyncing: false,
    }},
    methods: {
        syncAvatar() {
            this.isSyncing = true;

            $.ajax({
                type: 'POST',
                url: `/settings/profile/sync-avatar`,
            })
            .then(response => {
                toastr.info("sync was OK");

                let user = pillar.utils.getCurrentUser();
                user.avatar_url = response;
                pillar.utils.updateCurrentUser(user);
            })
            .catch(err => {
                toastr.error(xhrErrorResponseMessage(err), "There was an error syncing your avatar");
            })
            .then(() => {
                this.isSyncing = false;
            })
        },
    },
});
