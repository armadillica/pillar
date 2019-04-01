function thenGetNodes(where, embedded={}, sort='') {
    let encodedWhere = encodeURIComponent(JSON.stringify(where));
    let encodedEmbedded = encodeURIComponent(JSON.stringify(embedded));
    let encodedSort = encodeURIComponent(sort);

    return $.ajax({
        url: `/api/nodes?where=${encodedWhere}&embedded=${encodedEmbedded}&sort=${encodedSort}`,
        cache: false,
    });
}

function thenGetNode(nodeId) {
    return $.ajax({
        url: `/api/nodes/${nodeId}`,
        cache: false,
    });
}

function thenGetNodeActivities(nodeId, sort='[("_created", -1)]', max_results=20, page=1) {
    let encodedSort = encodeURIComponent(sort);
    return $.ajax({
        url: `/api/nodes/${nodeId}/activities?sort=${encodedSort}&max_results=${max_results}&page=${page}`,
        cache: false,
    });
}

function thenUpdateNode(node) {
    let id = node['_id'];
    let etag = node['_etag'];

    let nodeToSave = removePrivateKeys(node);
    let data = JSON.stringify(nodeToSave);
    return $.ajax({
        url: `/api/nodes/${id}`,
        type: 'PUT',
        data: data,
        dataType: 'json',
        contentType: 'application/json; charset=UTF-8',
        headers: {'If-Match': etag},
    }).then(updatedInfo => {
        return thenGetNode(updatedInfo['_id'])
        .then(node => {
            pillar.events.Nodes.triggerUpdated(node);
            return node;
        })
    });
}

function thenDeleteNode(node) {
    let id = node['_id'];
    let etag = node['_etag'];

    return $.ajax({
        url: `/api/nodes/${id}`,
        type: 'DELETE',
        headers: {'If-Match': etag},
    }).then(() => {
        pillar.events.Nodes.triggerDeleted(id);
    });
}

function removePrivateKeys(doc) {
    function doRemove(d) {
        for (const key in d) {
            if (key.startsWith('_')) {
                delete d[key];
                continue;
            }
            let val = d[key];
            if(typeof val === 'object') {
                doRemove(val);
            }
        }
    }
    let docCopy = JSON.parse(JSON.stringify(doc));
    doRemove(docCopy);
    delete docCopy['allowed_methods']

    return docCopy;
}

export { thenGetNodes, thenGetNode, thenGetNodeActivities, thenUpdateNode, thenDeleteNode }
