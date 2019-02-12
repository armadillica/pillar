const TEMPLATE =`
<div class="pillar-table-column"/>
`;

Vue.component('pillar-table-column', {
    template: TEMPLATE,
    props: {
        column: Object
    },
});
