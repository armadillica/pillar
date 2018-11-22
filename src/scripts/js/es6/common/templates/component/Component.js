import { ComponentCreatorInterface } from './ComponentCreatorInterface'

const REGISTERED_CREATORS = []

export class Component extends ComponentCreatorInterface {
    static create$listItem(doc) {
        let creator = Component.getCreator(doc);
        return creator.create$listItem(doc);
    }

    static create$item(doc) {
        let creator = Component.getCreator(doc);
        return creator.create$item(doc);
    }

    static canCreate(candidate) {
        return !!Component.getCreator(candidate);
    }

    static regiseterCreator(creator) {
        REGISTERED_CREATORS.push(creator);
    }

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