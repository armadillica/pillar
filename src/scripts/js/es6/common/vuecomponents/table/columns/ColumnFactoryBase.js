/**
 * Provides the columns that are available in a table.
 */
class ColumnFactoryBase{
    /**
     * To be overridden for your purposes
     * @returns {Promise(ColumnBase)} The columns that are available in the table.
     */
    thenGetColumns() {
        throw Error('Not implemented')
    }
}

export { ColumnFactoryBase }

