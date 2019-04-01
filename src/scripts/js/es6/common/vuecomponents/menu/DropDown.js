const TEMPLATE =`
<div class="pillar-dropdown">
    <div class="pillar-dropdown-button action"
        :class="buttonClasses"
        @click="toggleShowMenu"
    >
        <slot name="button"/>
    </div>
    <div class="pillar-dropdown-menu"
        v-show="showMenu"
        v-click-outside="closeMenu"
    >
        <slot name="menu"/>
    </div>
</div>
`;

let DropDown = Vue.component('pillar-dropdown', {
    template: TEMPLATE,
    data() {
        return {
            showMenu: false
        }
    },
    computed: {
        buttonClasses() {
            return {'is-open': this.showMenu};
        }
    },
    methods: {
        toggleShowMenu(event) {
            event.preventDefault();
            event.stopPropagation();
            this.showMenu = !this.showMenu;
        },
        closeMenu(event) {
            this.showMenu = false;
        }
    },
});

export { DropDown }
