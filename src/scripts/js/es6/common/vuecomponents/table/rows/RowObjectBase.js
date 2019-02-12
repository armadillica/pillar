class RowBase {
    constructor(underlyingObject) {
        this.underlyingObject = underlyingObject;
        this.isInitialized = false;
    }

    thenInit() {
        this.isInitialized = true
        return Promise.resolve();
    }

    getName() {
        return this.underlyingObject.name;
    }

    getId() {
        return this.underlyingObject._id;
    }

    getProperties() {
        return this.underlyingObject.properties;
    }

    getRowClasses() {
        return {
            "is-busy": !this.isInitialized
        }
    }
}

export { RowBase }
