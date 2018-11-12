
let CREATE_NODE_ITEM_MAP = {}

class Nodes {
    static create$listItem(node) {
        return CREATE_NODE_ITEM_MAP[node.node_type].create$listItem(node);
    }

    static create$item(node) {
        return CREATE_NODE_ITEM_MAP[node.node_type].create$item(node);
    }

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

    static registerTemplate(key, klass) {
        CREATE_NODE_ITEM_MAP[key] = klass;
    }
}

class NodesFactoryInterface{
    static create$listItem(node) {
        throw 'Not Implemented'
    }

    static create$item(node) {
        throw 'Not Implemented'
    }
}

export { Nodes, NodesFactoryInterface };