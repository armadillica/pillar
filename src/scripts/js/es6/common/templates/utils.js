function thenLoadVideoProgress(nodeId) {
    return $.get('/api/users/video/' + nodeId + '/progress')
}

export { thenLoadVideoProgress };
