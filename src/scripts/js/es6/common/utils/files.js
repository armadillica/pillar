function thenLoadImage(imgId, size = 'm') {
    return $.get('/api/files/' + imgId)
            .then((resp)=> {
                var show_variation = null;
                if (typeof resp.variations != 'undefined') {
                    for (var variation of resp.variations) {
                        if (variation.size != size) continue;
                        show_variation = variation;
                        break;
                    }
                }

                if (show_variation == null) {
                    throw 'Image not found: ' + imgId + ' size: ' + size;
                }
                return show_variation;
            })
}

export { thenLoadImage }
