$(function() {
    /* Expand images when their link points to a jpg/png/gif/webp */
    var imgs = $('.expand-image-links a img')
    .off('click')
    .on('click', function(e){
        var $img = $(this);
        var href = $img.parent().attr('href');

        if (href.match("\\.(jpg|png|gif|webp)\\W?")) {
            var src = $img.attr('src');
            var overlay_img = $('<img>').attr('src', src);
            $('#page-overlay')
                        .addClass('active')
                        .html(overlay_img);
            e.preventDefault();
        }
    });
});
