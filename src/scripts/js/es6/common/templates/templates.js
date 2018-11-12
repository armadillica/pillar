import { Nodes } from './nodes';
import { Assets } from './assets';
import { Posts } from './posts';

Nodes.registerTemplate('asset', Assets);
Nodes.registerTemplate('post', Posts);

export { Nodes };