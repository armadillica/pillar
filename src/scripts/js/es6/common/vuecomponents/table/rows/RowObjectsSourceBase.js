class RowObjectsSourceBase {
    constructor(projectId) {
        this.projectId = projectId;
        this.rowObjects = [];
    }

    // Override this
    thenFetchObjects() {
        throw Error('Not implemented');
    }

    thenInit() {
        return Promise.all(
            this.rowObjects.map(it => it.thenInit())
        );
    }
}

export { RowObjectsSourceBase }
