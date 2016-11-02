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

    /**
     * Marks the queried buttons as "Add New Attachment" buttons.
     */
    $.fn.addNewAttachmentButton = function() {
        var $button = this;
        $button.click(function() {
            console.log('Cloning last repeating group');
            var lastRepeatingGroup = $button
                .parent()
                .next('.attachments')
                .children('ul.fieldlist')
                .children('li')
                .last();
            console.log(lastRepeatingGroup.toArray());
            var cloned = lastRepeatingGroup.clone(false);
            cloned.insertAfter(lastRepeatingGroup);
            resetAttributeNames(cloned);
            cloned.find('.fileupload').each(setup_file_uploader)
        })
    }
}(jQuery));
