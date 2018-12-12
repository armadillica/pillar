function thenMarkdownToHtml(markdown, attachments={}) {
    let data = JSON.stringify({
        content: markdown,
        attachments: attachments
    });
    return $.ajax({
        url: "/nodes/preview-markdown",
        type: 'POST',
        headers: {"X-CSRFToken": csrf_token},
        headers: {},
        data: data,
        dataType: 'json',
        contentType: 'application/json; charset=UTF-8'
    })
}

export { thenMarkdownToHtml }