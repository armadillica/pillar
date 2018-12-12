function thenUploadFile(projectId, file, progressCB=(total, loaded)=>{}) {
    let formData = createFormData(file)
    return $.ajax({
        url: `/api/storage/stream/${projectId}`,
        type: 'POST',
        data: formData,

        cache: false,
        contentType: false,
        processData: false,

        xhr: () => {
            let myxhr = $.ajaxSettings.xhr();
            if (myxhr.upload) {
                // For handling the progress of the upload
                myxhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        progressCB(e.total, e.loaded);
                    }
                }, false);
            }
            return myxhr;
        }
    });
}

function createFormData(file) {
    let formData = new FormData();
    formData.append('file', file);

    return formData;
}

function thenGetFileDocument(fileId) {
    return $.get(`/api/files/${fileId}`);
}

function getFileVariation(fileDoc, size = 'm') {
    var show_variation = null;
    if (typeof fileDoc.variations != 'undefined') {
        for (var variation of fileDoc.variations) {
            if (variation.size != size) continue;
            show_variation = variation;
            break;
        }
    }

    if (show_variation == null) {
        throw 'Image not found: ' + fileDoc._id + ' size: ' + size;
    }
    return show_variation;
}

export { thenUploadFile, thenGetFileDocument, getFileVariation }