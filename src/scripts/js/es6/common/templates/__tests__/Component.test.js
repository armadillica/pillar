import { Assets } from '../nodes/Assets'
import { Users } from '../users/Users'
import { Component } from '../init' // Component is initialized in init

describe('Component', () => {
    test('can create Users listItem', () => {
        let userDoc = {
            _id: 'my-user-id',
            username: 'My User Name',
            full_name: 'My full name',
            roles: ['admin', 'subscriber']
        };
        
        let $user_actual = Component.create$listItem(userDoc);
        expect($user_actual.length).toBe(1);
        
        let $user_reference = Users.create$listItem(userDoc);
        expect($user_actual).toEqual($user_reference);
    });

    test('can create Asset listItem', () => {
        let nodeDoc = {
            _id: 'my-asset-id',
            name: 'My Asset',
            node_type: 'asset',
            project: {
                name: 'My Project',
                url: 'url-to-project'
            },
            properties: {
                content_type: 'image'
            }
        };
        
        let $asset_actual = Component.create$listItem(nodeDoc);
        expect($asset_actual.length).toBe(1);
        
        let $asset_reference = Assets.create$listItem(nodeDoc);
        expect($asset_actual).toEqual($asset_reference);
    });

    test('fail to create unknown', () => {
        expect(()=>Component.create$listItem({})).toThrow('Can not create component using: {}')
        expect(()=>Component.create$listItem()).toThrow('Can not create component using: undefined')
        expect(()=>Component.create$listItem({strange: 'value'}))
            .toThrow('Can not create component using: {"strange":"value"}')
    });
});