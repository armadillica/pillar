/**
 * @deprecated use vue instead
 */
export class ComponentCreatorInterface {
    /**
     * Create a $element to render document in a list
     * @param {Object} doc
     * @returns {$element}
     */
    static create$listItem(doc) {
        throw 'Not Implemented';
    }

    /**
     * Create a $element to render the full doc
     * @param {Object} doc
     * @returns {$element}
     */
    static create$item(doc) {
        throw 'Not Implemented';
    }

    /**
     * @param {Object} candidate
     * @returns {boolean}
     */
    static canCreate(candidate) {
        throw 'Not Implemented';
    }
}
