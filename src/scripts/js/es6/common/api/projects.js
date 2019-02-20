function thenGetProject(projectId) {
    return $.get(`/api/projects/${projectId}`);
}

export { thenGetProject }
