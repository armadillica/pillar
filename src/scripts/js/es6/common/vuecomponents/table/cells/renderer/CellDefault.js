import {ColumnBase} from '../../columns/ColumnBase'
import {RowBase} from '../../rows/RowObjectBase'

const TEMPLATE =`
<div>
    {{ cellValue }}
</div>
`;

/**
 * Default cell renderer. Takes raw cell value and formats it.
 * Override for custom formatting of value.
 */
let CellDefault = Vue.component('pillar-cell-default', {
    template: TEMPLATE,
    props: {
        column: ColumnBase,
        rowObject: RowBase,
        rawCellValue: [String,Number,Boolean,Array,Object,Date,Function,Symbol,],
    },
    computed: {
        cellValue() {
            return this.rawCellValue;
        }
    },
});

export { CellDefault }
