/**
 * Little API for managing the document title.
 *
 * This allows the document title to be composed of individually adjustable
 * properties.
 */
var DocumentTitleAPI = {
	// Properties that make up the document title:
	page_title: document.title,
	notification_count: 0,

	// Updates the page title given the current state.
	update: function() {
		if (this.notification_count > 0){
			document.title = '(' + this.notification_count + ') ' + this.page_title;
		} else {
			document.title = this.page_title;
		}
	},

	// Sets just the notification count and updates the document title.
	set_notification_count: function(new_notif_count) {
		this.notification_count = new_notif_count;
		this.update();
	},

	// Sets just the page title and updates the document title.
	set_page_title: function(new_page_title) {
		this.page_title = new_page_title;
		this.update();
	},
};


/* Status Bar * DEPRECATED * USE TOASTR INSTEAD */
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

/* Status Bar * DEPRECATED - USE TOASTR INSTEAD * */
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


/* Loading Bar
 * Sets .loader-bar in layout.pug as active when
 * loading an asset or performing actions.
 */
function loadingBarShow(){
	$('.loading-bar').addClass('active');
}

function loadingBarHide(){
	$('.loading-bar').removeClass('active');
}
