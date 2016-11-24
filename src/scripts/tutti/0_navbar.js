if(typeof($.fn.popover) != 'undefined'){
	$('[data-toggle="popover"]').popover();
}
if(typeof($.fn.tooltip) != 'undefined'){
	$('[data-toggle="tooltip"]').tooltip({'delay' : {'show': 0, 'hide': 0}});
}

/* Status Bar */
function statusBarClear(delay_class, delay_html){
	var statusBar = $("#status-bar");

	if (!delay_class) { delay_class = 0 };
	if (!delay_html) { delay_html = 250 };

	if (delay_class == 0) {
		statusBar.removeAttr('class');
		return

	} else {
		setTimeout(function(){
			statusBar.removeAttr('class');

			setTimeout(function() {
				statusBar.html('');
			}, delay_html);
		}, delay_class);
	}
}

function statusBarSet(classes, html, icon_name, time){
	/* Utility to notify the user by temporarily flashing text on the project header
		 Usage:
			'classes' can be: success, error, warning, info, default
			'html': the text to display, can contain html tags
				(in case of errors, it's better to use data.status + data.statusText instead )
			'icon_name': optional, sets a custom icon (otherwise an icon based on the class will be used)
			'time': optional, custom time in milliseconds for the text to be displayed
	*/

	var icon = '';

	if (!time) { time = 3000 };

	if (!icon_name) {
		if (classes == 'error') {
			icon_name = 'pi-attention';
		} else if (classes == 'success') {
			icon_name = 'pi-check';
		} else if (classes == 'warning') {
			icon_name = 'pi-warning';
		} else if (classes == 'info') {
			icon_name = 'pi-info';
		} else {
			icon = '<i class="' + icon_name + '"></i>';
		};
	} else {
		icon = '<i class="' + icon_name + '"></i>';
	};

	statusBarClear(0,0);

	var text = icon + html;
	var statusBar = $("#status-bar");

	statusBar
		.addClass('active ' + classes)
		.html(text);

	/* Back to normal */
	statusBarClear(time, 250);
};

