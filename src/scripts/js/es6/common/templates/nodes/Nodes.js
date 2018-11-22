import { NodesBase } from './NodesBase';
import { ComponentCreatorInterface } from '../component/ComponentCreatorInterface'

let CREATE_NODE_ITEM_MAP = {}

export class Nodes extends ComponentCreatorInterface {
    /**
     * Creates a small list item out of a node document
     * @param {NodeDoc} node mongodb or elastic node document
     */
    static create$listItem(node) {
        let factory = CREATE_NODE_ITEM_MAP[node.node_type] || NodesBase;
        return factory.create$listItem(node);
    }

    /**
     * Creates a full view out of a node document
     * @param {NodeDoc} node mongodb or elastic node document
     */
    static create$item(node) {
        let factory = CREATE_NODE_ITEM_MAP[node.node_type] || NodesBase;
        return factory.create$item(node);
    }

    /**
     * Creates a list of items and a 'Load More' button
     * @param {List} nodes A list of nodes to be created
     * @param {Int} initial Number of nodes to show initially
     * @param {Int} loadNext Number of nodes to show when clicking 'Load More'. If 0, no load more button will be shown
     */
    static createListOf$nodeItems(nodes, initial=8, loadNext=8) {
        let nodesLeftToRender = nodes.slice();
        let nodesToCreate = nodesLeftToRender.splice(0, initial);
        let listOf$items = nodesToCreate.map(Nodes.create$listItem);

        if (loadNext > 0 && nodesLeftToRender.length) {
            let $link = $('<a>')
                .addClass('btn btn-outline-primary px-5 mb-auto btn-block js-load-next')
                .attr('href', 'javascript:void(0);')
                .click((e)=> { 
                    let $target = $(e.target);
                    $target.replaceWith(Nodes.createListOf$nodeItems(nodesLeftToRender, loadNext, loadNext));
                 })
                .text('Load More');

            listOf$items.push($link);
        }
        return listOf$items;
    }

    static canCreate(candidate) {
        return !!candidate.node_type;
    }

    /**
     * Register template classes to handle the cunstruction of diffrent node types
     * @param { String } node_type The node type whose template that is registered
     * @param { NodesBase } klass The class to handle the creation of jQuery objects
     */
    static registerTemplate(node_type, klass) {
        CREATE_NODE_ITEM_MAP[node_type] = klass;
    }
}