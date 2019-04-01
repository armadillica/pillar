const TEMPLATE = `
<div class="user-avatar">
    <img
        :src="user.gravatar"
        :alt="user.full_name">
</div>
`;

let UserAvatar = Vue.component('user-avatar', {
    template: TEMPLATE,
    props: {user: Object},
});

export {UserAvatar}
