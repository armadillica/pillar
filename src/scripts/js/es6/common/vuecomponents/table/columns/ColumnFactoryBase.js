/**
 * Provides the columns that are available in a table.
 */
class ColumnFactoryBase{
    constructor(projectId) {
        this.projectId = projectId;
        this.projectPromise;
    }

    /**
     * To be overridden for your purposes
     * @returns {Promise(ColumnBase)} The columns that are available in the table.
     */
    thenGetColumns() {
        throw Error('Not implemented')
    }

    thenGetProject() {
        if (this.projectPromise) {
            return this.projectPromise;
        }
        this.projectPromise = pillar.api.thenGetProject(this.projectId);
        return this.projectPromise;
    }
}

export { ColumnFactoryBase }

