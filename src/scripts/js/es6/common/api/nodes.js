function thenGetNodes(where, embedded={}, sort='') {
    let encodedWhere = encodeURIComponent(JSON.stringify(where));
    let encodedEmbedded = encodeURIComponent(JSON.stringify(embedded));
    let encodedSort = encodeURIComponent(sort);

    return $.get(`/api/nodes?where=${encodedWhere}&embedded=${encodedEmbedded}&sort=${encodedSort}`);
}

export { thenGetNodes }
