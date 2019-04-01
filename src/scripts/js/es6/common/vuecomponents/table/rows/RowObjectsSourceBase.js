/**
 * The provider of RowObjects to a table.
 * Extend to fit your purpose.
 */
class RowObjectsSourceBase {
    constructor() {
        this.rowObjects = [];
    }

    /**
     * Should be overriden to fetch and create the row objects to we rendered in the table. The Row objects should be stored in
     * this.rowObjects
     */
    thenGetRowObjects() {
        throw Error('Not implemented');
    }

    /**
     * Inits all its row objects.
     */
    thenInit() {
        return Promise.all(
            this.rowObjects.map(it => it.thenInit())
        );
    }
}

export { RowObjectsSourceBase }
