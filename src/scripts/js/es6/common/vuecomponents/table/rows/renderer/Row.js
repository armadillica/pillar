import '../../cells/renderer/CellProxy'


const TEMPLATE =`
<div class="pillar-table-row"
    :class="rowClasses"
    @click.prevent.stop="$emit('item-clicked', arguments[0], rowObject.getId())"
>
    <pillar-cell-proxy
        v-for="c in columns"
        :rowObject="rowObject"
        :column="c"
        :key="c._id"
        @item-clicked="$emit('item-clicked', ...arguments)"
    />
</div>
`;
/**
 * @emits item-clicked(mouseEvent,itemId) When a RowObject has been clicked
 */
Vue.component('pillar-table-row', {
    template: TEMPLATE,
    props: {
        rowObject: Object,
        columns: Array
    },
    computed: {
        rowClasses() {
            let classes = this.rowObject.getRowClasses()
            classes['active'] = this.rowObject.isSelected;
            return classes;
        }
    },
});
