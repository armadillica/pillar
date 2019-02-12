class RowObjectsSourceBase {
    constructor(projectId) {
        this.projectId = projectId;
        this.rowObjects = [];
    }

    // Override this
    thenInit() {
        throw Error('Not implemented');
    }
}

export { RowObjectsSourceBase }
