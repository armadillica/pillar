import { ComponentCreatorInterface } from '../component/ComponentCreatorInterface'

export class Users extends ComponentCreatorInterface {
    static create$listItem(userDoc) {
        let roles = userDoc.roles || [];
        return $('<div>')
            .addClass('users p-2 border-bottom')
            .attr('data-user-id', userDoc._id || userDoc.objectID )
            .append(
                $('<h6>')
                    .addClass('mb-0 font-weight-bold')
                    .text(userDoc.full_name),
                $('<small>')
                    .text(userDoc.username),
                $('<small>')
                    .addClass('d-block roles text-info')
                    .text(roles.join(', '))
            )
    }

    static canCreate(candidate) {
        return !!candidate.username;
    }
}
