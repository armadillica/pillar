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

    /***** Attachment handling ******/
    var attrs = ['for', 'id', 'name', 'data-field-name', 'data-field-slug'];
    function resetAttributeNames(section) {
        var tags = section.find('input, select, label, div, a');
        var idx = section.index();

        tags.each(function () {
            var $this = $(this);

            // Renumber certain attributes.
            $.each(attrs, function (i, attr) {
                var attr_val = $this.attr(attr);
                if (attr_val) {
                    $this.attr(attr, attr_val.replace(/-\d+/, '-' + idx))
                }
            });

            // Clear input field values
            var tagname = $this.prop('tagName');
            if (tagname == 'INPUT') {
                if ($this.attr('type') == 'checkbox') {
                    $this.prop('checked', false);
                } else {
                    $this.val('');
                }
            } else if (tagname == 'SELECT') {
                $this.find(':nth-child(1)').prop('selected', true);
            }
        });

        // Click on all file delete buttons to clear all file widgets.
        section.find('a.file_delete').click();
        section.find('div.form-upload-progress-bar').hide();
    }

    /**
     * Marks the queried buttons as "Add New Attachment" or
     * "Add New File" button.
     */
    $.fn.addNewFileButton = function() {
        var $button = this;
        $button.click(function() {
            var lastRepeatingGroup = $button
                .parent()
                .next('.form-group')
                .children('ul.fieldlist')
                .children('li')
                .last();
            var cloned = lastRepeatingGroup.clone(false);
            cloned.insertAfter(lastRepeatingGroup);
            resetAttributeNames(cloned);
            cloned.find('.fileupload').each(setup_file_uploader)
        })
    }

}(jQuery));
