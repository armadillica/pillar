function deleteFile(fileField, newFileId) {
    if (newFileId) {
        fileField.val(newFileId);
    } else {
        fileField.val('');
    }
}

var current_file_uploads = 0;

function on_file_upload_activated() {
    if (current_file_uploads == 0) {
        // Disable the save buttons.
        $('.button-save')
            .addClass('disabled')
            .find('a').html('<i class="pi-spin spin"></i> Uploading...');
    }

    current_file_uploads++;
}

function on_file_upload_finished() {
    current_file_uploads = Math.max(0, current_file_uploads-1);

    if (current_file_uploads == 0) {
        // Restore the save buttons.
        $('.button-save')
            .removeClass('disabled')
            .find('a').html('<i class="pi-check"></i> Save Changes');
    }
}


function setup_file_uploader(index, upload_element) {
    var $upload_element = $(upload_element);
    var container = $upload_element.parent().parent();
    var progress_bar = container.find('div.form-upload-progress-bar');

    function set_progress_bar(progress, html_class) {
        progress_bar.css({
            'width': progress + '%',
            'display': progress == 0 ? 'none' : 'block'});

        progress_bar.removeClass('progress-error progress-uploading progress-processing');
        if (!!html_class) progress_bar.addClass(html_class);
    }

    $upload_element.fileupload({
        dataType: 'json',
        replaceFileInput: false,
        dropZone: container,
        formData: {},
        beforeSend: function (xhr, data) {
            var token = this.fileInput.attr('data-token');
            xhr.setRequestHeader('Authorization', 'basic ' + btoa(token + ':'));
            statusBarSet('info', 'Uploading File...', 'pi-upload-cloud');

            // console.log('Uploading from', upload_element, upload_element.value);

            // Clear thumbnail & progress bar.
            container.find('.preview-thumbnail').hide();
            set_progress_bar(0);

            $('body').trigger('file-upload:activated');
        },
        add: function (e, data) {
            var uploadErrors = [];
            // Load regex if available (like /^image\/(gif|jpe?g|png)$/i;)
            var acceptFileTypes = new RegExp($(this).data('file-format'));
            if (data.originalFiles[0]['type'].length && !acceptFileTypes.test(data.originalFiles[0]['type'])) {
                uploadErrors.push('Not an accepted file type');
            }
            if (uploadErrors.length > 0) {
                $(this).parent().parent().addClass('error');
                $(this).after(uploadErrors.join("\n"));
            } else {
                $(this).parent().parent().removeClass('error');
                data.submit();
            }
        },
        progressall: function (e, data) {
            // Update progressbar during upload
            var progress = parseInt(data.loaded / data.total * 100, 10);
            // console.log('Uploading', upload_element.value, ': ', progress, '%');

            set_progress_bar(Math.max(progress, 2),
                progress > 99.9 ? 'progress-processing' : 'progress-uploading'
            );
        },
        done: function (e, data) {
            if (data.result.status !== 'ok') {
                if (console)
                    console.log('FIXME, do error handling for non-ok status', data.result);
                return;
            }

            // Ensure the form refers to the correct Pillar file ID.
            var pillar_file_id = data.result.file_id;
            var $file_id_field = $('#' + $(this).attr('data-field-name'));
            if ($file_id_field.val()) {
                deleteFile($file_id_field, pillar_file_id);
            }
            $file_id_field.val(pillar_file_id);

            var filename = data.files[0].name;

            // Set the slug based on the name, strip special characters
            $('#' + $(this).attr('data-field-slug')).val(filename.replace(/[^0-9a-zA-Z]+/g, ""));

            // Ugly workaround: If the asset has the default name, name it as the file
            if ($('.form-group.name .form-control').val() == 'New asset') {
                $('.form-group.name .form-control').val(filename);
                $('.node-edit-title').html(filename);
            }

            statusBarSet('success', 'File Uploaded Successfully', 'pi-check');
            set_progress_bar(100);

            $('body').trigger('file-upload:finished');
        },
        fail: function (jqXHR, fileupload) {
            if (console) {
                console.log('Upload error:');
                console.log('jqXHR', jqXHR);
                console.log('fileupload', fileupload);
            }

            var uploadErrors = [];
            for (var key in fileupload.messages) {
                uploadErrors.push(fileupload.messages[key]);
            }

            statusBarSet('error',
                         'Upload error: ' + uploadErrors.join("; "),
                         'pi-attention', 16000);

            set_progress_bar(100, 'progress-error');

            $('body').trigger('file-upload:finished');
        }
    });
}


$(function () {
    // $('.file_delete').click(function(e){
    $('body').unbind('click')
        .on('click', '.file_delete', function(e) {
            e.preventDefault();
            var field_name = '#' + $(this).data('field-name');
            var file_field = $(field_name);
            deleteFile(file_field);
            $(this).parent().parent().hide();
            $(this).parent().parent().prev().hide();
        })
        .on('file-upload:activated', on_file_upload_activated)
        .on('file-upload:finished', on_file_upload_finished)
        .on('click', '.js-append-attachment', function(e) {
            e.preventDefault();

            // Append widget @[slug-name] to the post's description
            // Note: Heavily connected to HTML in _node_edit_form.jade
            var slug = $(this).parent().find("input[id*='slug']").val();
            var widget = '@[' + slug + ']\n';

            if (slug) {
                document.getElementById('description').value += widget;
                statusBarSet('success', 'Attachment appended to description', 'pi-check');
            } else {
                statusBarSet('error', 'Slug is empty, upload something first', 'pi-warning');
            }
        })
    ;

    function inject_project_id_into_url(index, element) {
        // console.log('Injecting ', ProjectUtils.projectId(), ' into ', element);
        var url = element.getAttribute('data-url');
        url = url.replace('{project_id}', ProjectUtils.projectId());
        element.setAttribute('data-url', url);
        // console.log('The new element is', element);
    }

    $('.fileupload')
        .each(inject_project_id_into_url)
        .each(setup_file_uploader)
    ;
});
