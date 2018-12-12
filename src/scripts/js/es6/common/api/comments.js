function thenGetComments(parentId) {
    return $.getJSON(`/api/nodes/${parentId}/comments`);
}

function thenCreateComment(parentId, msg, attachments) {
    let data = JSON.stringify({
        msg: msg,
        attachments: attachments
    });
    return $.ajax({
        url: `/api/nodes/${parentId}/comments`,
        type: 'POST',
        data: data,
        dataType: 'json',
        contentType: 'application/json; charset=UTF-8'
    });
}

function thenUpdateComment(parentId, commentId, msg, attachments) {
    let data = JSON.stringify({
        msg: msg,
        attachments: attachments
    });
    return $.ajax({
        url: `/api/nodes/${parentId}/comments/${commentId}`,
        type: 'PATCH',
        data: data,
        dataType: 'json',
        contentType: 'application/json; charset=UTF-8'
    });
}

function thenVoteComment(parentId, commentId, vote) {
    let data = JSON.stringify({
        vote: vote
    });
    return $.ajax({
        url: `/api/nodes/${parentId}/comments/${commentId}/vote`,
        type: 'POST',
        data: data,
        dataType: 'json',
        contentType: 'application/json; charset=UTF-8'
    });
}

export { thenGetComments, thenCreateComment, thenUpdateComment, thenVoteComment }