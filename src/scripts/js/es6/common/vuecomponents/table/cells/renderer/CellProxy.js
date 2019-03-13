const TEMPLATE =`
<component class="pillar-cell"
    :class="cellClasses"
    :title="cellTitle"
    :is="cellRenderer"
    :rowObject="rowObject"
    :column="column"
    :rawCellValue="rawCellValue"
    @item-clicked="$emit('item-clicked', ...arguments)"
/>
`;

let CellProxy = Vue.component('pillar-cell-proxy', {
    template: TEMPLATE,
    props: {
        column: Object,
        rowObject: Object
    },
    computed: {
        rawCellValue() {
            return this.column.getRawCellValue(this.rowObject) || '';
        },
        cellRenderer() {
            return this.column.getCellRenderer(this.rowObject);
        },
        cellClasses() {
            return this.column.getCellClasses(this.rawCellValue, this.rowObject);
        },
        cellTitle() {
            return this.column.getCellTitle(this.rawCellValue, this.rowObject);
        }
    },
});

export { CellProxy }
