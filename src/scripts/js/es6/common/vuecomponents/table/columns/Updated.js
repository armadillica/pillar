import { CellPrettyDate } from '../cells/renderer/CellPrettyDate'
import {ColumnBase} from './ColumnBase'

/**
 * Column showing the objects _updated prettyfied
 */

export class Updated extends ColumnBase{
    constructor() {
        super('Updated', 'row-updated');
        this.includedByDefault = false;
    }

    /**
     *
     * @param {RowObject} rowObject
     * @returns {String} Name of the Cell renderer component
     */
    getCellRenderer(rowObject) {
        return CellPrettyDate.options.name;
    }

    /**
     *
     * @param {RowObject} rowObject
     * @returns {DateString}
     */
    getRawCellValue(rowObject) {
        return rowObject.underlyingObject['_updated'];
    }

    /**
     * Cell tooltip
     * @param {Any} rawCellValue
     * @param {RowObject} rowObject
     * @returns {String}
     */
    getCellTitle(rawCellValue, rowObject) {
        return rawCellValue;
    }

    /**
     * Compare  two rows to sort them. Can be overridden for more complex situations.
     *
     * @param {RowObject} rowObject1
     * @param {RowObject} rowObject2
     * @returns {Number} -1, 0, 1
     */
    compareRows(rowObject1, rowObject2) {
        let dueDateStr1 = this.getRawCellValue(rowObject1);
        let dueDateStr2 = this.getRawCellValue(rowObject2);
        if (dueDateStr1 === dueDateStr2) return 0;
        if (dueDateStr1 && dueDateStr2) {
            return new Date(dueDateStr1) < new Date(dueDateStr2) ? -1 : 1;
        }
        return dueDateStr1 ? -1 : 1;
    }
}
