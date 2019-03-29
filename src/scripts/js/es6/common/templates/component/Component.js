import { ComponentCreatorInterface } from './ComponentCreatorInterface'

const REGISTERED_CREATORS = []

/**
 * Create a jQuery renderable element from a mongo document using registered creators.
 * @deprecated use vue instead
 */
export class Component extends ComponentCreatorInterface {
    /**
     *
     * @param {Object} doc
     * @returns {$element}
     */
    static create$listItem(doc) {
        let creator = Component.getCreator(doc);
        return creator.create$listItem(doc);
    }

    /**
     * @param {Object} doc
     * @returns {$element}
     */
    static create$item(doc) {
        let creator = Component.getCreator(doc);
        return creator.create$item(doc);
    }

    /**
     * @param {Object} candidate
     * @returns {Boolean}
     */
    static canCreate(candidate) {
        return !!Component.getCreator(candidate);
    }

    /**
     * Register component creator to handle a node type
     * @param {ComponentCreatorInterface} creator
     */
    static regiseterCreator(creator) {
        REGISTERED_CREATORS.push(creator);
    }

    /**
     * @param {Object} doc
     * @returns {ComponentCreatorInterface}
     */
    static getCreator(doc) {
        if (doc) {
            for (let candidate of REGISTERED_CREATORS) {
                if (candidate.canCreate(doc)) {
                    return candidate;
                }
            }
        }
        throw 'Can not create component using: ' + JSON.stringify(doc);
    }
}
