import {DateColumnBase} from './DateColumnBase'

/**
 * Column showing the objects _created prettyfied
 */
export class Created extends DateColumnBase{
    constructor() {
        super('Created', 'row-created');
        this.includedByDefault = false;
    }
    /**
     *
     * @param {RowObject} rowObject
     * @returns {DateString}
     */
    getRawCellValue(rowObject) {
        return rowObject.underlyingObject['_created'];
    }
}
