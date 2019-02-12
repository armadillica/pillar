import { CellDefault } from './CellDefault'

let CellPrettyDate = Vue.component('pillar-cell-pretty-date', {
    extends: CellDefault,
    computed: {
        cellValue() {
            return pillar.utils.prettyDate(this.rawCellValue);
        }
    }
});

export { CellPrettyDate }
