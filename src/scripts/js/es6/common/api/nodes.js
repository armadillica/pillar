function thenGetNodes(where, embedded={}) {
    let encodedWhere = encodeURIComponent(JSON.stringify(where));
    let encodedEmbedded = encodeURIComponent(JSON.stringify(embedded));

    return $.get(`/api/nodes?where=${encodedWhere}&embedded=${encodedEmbedded}`);
}

export { thenGetNodes }
