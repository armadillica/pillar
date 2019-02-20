class ColumnFactoryBase{
    constructor(projectId) {
        this.projectId = projectId;
        this.projectPromise;
    }

    // Override this
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
