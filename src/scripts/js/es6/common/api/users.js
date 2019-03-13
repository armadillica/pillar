function thenGetProjectUsers(projectId) {
    return $.ajax({
        url: `/api/p/users?project_id=${projectId}`,
    });
}

export { thenGetProjectUsers }
