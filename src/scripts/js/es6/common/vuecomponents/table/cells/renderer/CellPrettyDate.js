import { CellDefault } from './CellDefault'

/**
 * Formats raw values as "pretty date".
 * Expects rawCellValue to be a date.
 */
let CellPrettyDate = Vue.component('pillar-cell-pretty-date', {
    extends: CellDefault,
    computed: {
        cellValue() {
            return pillar.utils.prettyDate(this.rawCellValue);
        }
    }
});

export { CellPrettyDate }
