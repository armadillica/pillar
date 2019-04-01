import '../../cells/renderer/HeadCell'
const TEMPLATE =`
<div class="pillar-table-head">
    <pillar-head-cell
        v-for="c in columns"
        :column="c"
        key="c._id"
        @sort="(column, direction) => $emit('sort', column, direction)"
    />
</div>
`;
/**
 * @emits sort(column,direction) When a column head has been clicked
 */
Vue.component('pillar-table-head', {
    template: TEMPLATE,
    props: {
        columns: Array
    }
});
