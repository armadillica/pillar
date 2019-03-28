import {DateColumnBase} from './DateColumnBase'

/**
 * Column showing the objects _updated prettyfied
 */
export class Updated extends DateColumnBase{
    constructor() {
        super('Updated', 'row-updated');
        this.includedByDefault = false;
    }
    /**
     *
     * @param {RowObject} rowObject
     * @returns {DateString}
     */
    getRawCellValue(rowObject) {
        return rowObject.underlyingObject['_updated'];
    }
}
