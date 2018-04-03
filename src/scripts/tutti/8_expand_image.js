$(function() {

    function _expandImg(e) {
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
    }

    $.fn.expandOnClick = function() {
        $(this)
            .off('click')
            .on('click', _expandImg);
    };

    /* Expand images when their link points to a jpg/png/gif/webp */
    $('.expand-image-links a img').expandOnClick();
    $('a.expand-image-links img').expandOnClick();
});
