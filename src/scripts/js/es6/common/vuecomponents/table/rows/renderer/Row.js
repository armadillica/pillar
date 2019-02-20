import '../../cells/renderer/CellProxy'

const TEMPLATE =`
<div class="pillar-table-row"
    :class="rowClasses"
>
    <pillar-cell-proxy
        v-for="c in columns"
        :rowObject="rowObject"
        :column="c"
        :key="c._id"
    />
</div>
`;

Vue.component('pillar-table-row', {
    template: TEMPLATE,
    props: {
        rowObject: Object,
        columns: Array
    },
    computed: {
        rowClasses() {
            return this.rowObject.getRowClasses();
        }
    }
});
