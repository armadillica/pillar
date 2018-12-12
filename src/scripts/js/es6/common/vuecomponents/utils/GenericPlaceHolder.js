const TEMPLATE =
`<div class="generic-placeholder" :title="label">
    <i class="pi-spin spin"/>
    {{ label }}
</div>
`;

Vue.component('generic-placeholder', {
    template: TEMPLATE,
    props: {
        label: String,
    },
});