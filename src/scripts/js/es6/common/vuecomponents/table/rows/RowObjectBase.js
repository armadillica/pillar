/**
 * Each object to be visualized in the table is wrapped in a RowBase object. Column cells interact with it, 
 */
class RowBase {
    constructor(underlyingObject) {
        this.underlyingObject = underlyingObject;
        this.isInitialized = false;
        this.isSelected = false;
    }

    /**
     * Called after the row has been created to initalize async properties. Fetching child objects for instance
     */
    thenInit() {
        return this._thenInitImpl()
            .then(() => {
                this.isInitialized = true
            })
    }

    /**
     * Override to initialize async properties such as fetching child objects.
     */
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

    /**
     * The css classes that should be applied to the row in the table
     */
    getRowClasses() {
        return {
            "is-busy": !this.isInitialized
        }
    }

    /**
     * A row could have children (shots has tasks for example). Children should also be instances of RowObject
     */
    getChildObjects() {
        return [];
    }
}

export { RowBase }
