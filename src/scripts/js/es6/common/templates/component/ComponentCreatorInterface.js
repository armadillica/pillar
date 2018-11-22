export class ComponentCreatorInterface {
    /**
     * @param {JSON} doc 
     * @returns {$element}
     */
    static create$listItem(doc) {
        throw 'Not Implemented';
    }

    /**
     * 
     * @param {JSON} doc 
     * @returns {$element}
     */
    static create$item(doc) {
        throw 'Not Implemented';
    }

    /**
     * 
     * @param {JSON} candidate
     * @returns {boolean} 
     */
    static canCreate(candidate) {
        throw 'Not Implemented';
    }
}