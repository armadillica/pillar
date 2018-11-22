import { Nodes } from './nodes/Nodes';
import { Assets } from './nodes/Assets';
import { Posts } from './nodes/Posts';

import { Users } from './users/Users';
import { Component } from './component/Component';

Nodes.registerTemplate('asset', Assets);
Nodes.registerTemplate('post', Posts);

Component.regiseterCreator(Nodes);
Component.regiseterCreator(Users);

export {
    Nodes,
    Users,
    Component
};