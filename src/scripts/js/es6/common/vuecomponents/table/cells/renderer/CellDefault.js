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
        column: Object,
        rowObject: Object,
        rawCellValue: Object
    },
    computed: {
        cellValue() {
            return this.rawCellValue;
        }
    },
});

export { CellDefault }
