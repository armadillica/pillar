import { Users } from '../Users'

describe('Users', () => {
    let userDoc;
    describe('create$listItem', () => {
        beforeEach(()=>{
            userDoc = {
                _id: 'my-user-id',
                username: 'My User Name',
                full_name: 'My full name',
                roles: ['admin', 'subscriber']
            };
        });
        test('happy case', () => {
            let $user = Users.create$listItem(userDoc);
            expect($user.length).toBe(1);
            expect($user.hasClass('users')).toBeTruthy();
            expect($user.data('user-id')).toBe('my-user-id');

            let $username = $user.find(':contains(My User Name)');
            expect($username.length).toBe(1);

            let $fullName = $user.find(':contains(My full name)');
            expect($fullName.length).toBe(1);

            let $roles = $user.find('.roles');
            expect($roles.length).toBe(1);
            expect($roles.text()).toBe('admin, subscriber')
        });
    })

    describe('create$item', () => {
        beforeEach(()=>{
            userDoc = {
                _id: 'my-user-id',
                username: 'My User Name',
                full_name: 'My full name',
                roles: ['admin', 'subscriber']
            };
        });
        test('Not Implemented', () => {
            // Replace with proper test once implemented
            expect(()=>Users.create$item(userDoc)).toThrow('Not Implemented');
        });
    })
});
