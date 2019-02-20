const TEMPLATE =`
<div>
    {{ cellValue }}
</div>
`;

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
