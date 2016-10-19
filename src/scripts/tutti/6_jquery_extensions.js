(function ( $ ) {
    $.fn.flashOnce = function() {
        var target = this;
        this
            .addClass('flash-on')
            .delay(1000) // this delay is linked to the transition in the flash-on CSS class.
            .queue(function() {
                target
                    .removeClass('flash-on')
                    .addClass('flash-off')
                    .dequeue()
                ;})
            .delay(1000)  // this delay is just to clean up the flash-X classes.
            .queue(function() {
                target
                    .removeClass('flash-on flash-off')
                    .dequeue()
                ;})
        ;
        return this;
    };

    /**
     * Fades out the element, then erases its contents and shows the now-empty element again.
     */
    $.fn.fadeOutAndClear = function(fade_speed) {
        var target = this;
        this
            .fadeOut(fade_speed, function() {
                target
                    .html('')
                    .show();
            });
    }

    $.fn.scrollHere = function(scroll_duration_msec) {
        $('html, body').animate({
            scrollTop: this.offset().top
        }, scroll_duration_msec);
    }

}(jQuery));
