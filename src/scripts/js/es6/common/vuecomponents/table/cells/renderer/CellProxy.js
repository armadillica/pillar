import {RowBase} from '../../rows/RowObjectBase'
import {ColumnBase} from '../../columns/ColumnBase'

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

/**
 * Renders the cell that the column requests.
 *
 * @emits item-clicked(mouseEvent,itemId) Re-emits if real cell is emitting it
 */
let CellProxy = Vue.component('pillar-cell-proxy', {
    template: TEMPLATE,
    props: {
        column: ColumnBase,
        rowObject: RowBase,
    },
    computed: {
        /**
         * Raw unformated cell value
         */
        rawCellValue() {
            return this.column.getRawCellValue(this.rowObject) || '';
        },
        /**
         * Name of the cell render component to be rendered
         */
        cellRenderer() {
            return this.column.getCellRenderer(this.rowObject);
        },
        /**
         * Css classes to apply to the cell
         */
        cellClasses() {
            return this.column.getCellClasses(this.rawCellValue, this.rowObject);
        },
        /**
         * Cell tooltip
         */
        cellTitle() {
            return this.column.getCellTitle(this.rawCellValue, this.rowObject);
        }
    },
});

export { CellProxy }
