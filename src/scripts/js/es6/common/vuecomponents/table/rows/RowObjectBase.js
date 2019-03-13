class RowState {
    constructor(selectedIds) {
        this.selectedIds = selectedIds || [];
    }

    /**
     * 
     * @param {RowBase} rowObject 
     */
    applyState(rowObject) {
        rowObject.isSelected = this.selectedIds.includes(rowObject.getId());
    }
}

class RowBase {
    constructor(underlyingObject) {
        this.underlyingObject = underlyingObject;
        this.isInitialized = false;
        this.isVisible = true;
        this.isSelected = false;
    }


    thenInit() {
        return this._thenInitImpl()
            .then(() => {
                this.isInitialized = true
            })
    }

    _thenInitImpl() {
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

    getChildObjects() {
        return [];
    }
}

export { RowBase, RowState }
