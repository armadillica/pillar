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


$(document).ready(function() {

	/* Mobile check. */
	var isMobileScreen = window.matchMedia("only screen and (max-width: 760px)");

	function isMobile(){
		return isMobileScreen.matches;
	}

	// Every element that is a tab.
	$dropdownTabs = $('[data-dropdown-tab]');
	// Every menu element that toggles a tab.
	$dropdownTabsToggle = $('[data-toggle="dropdown-tab"]');

	function dropdownTabHideAll(){
		$dropdownTabs.removeClass('show');
	}

	function dropdownTabShow(tab){
		dropdownTabHideAll(); // First hide them all.
		$('[data-dropdown-tab="' + tab + '"]').addClass('show'); // Show the one we want.
	}

	// Mobile adjustments
	if (isMobile()) {
		// Add a class to the body for site-wide styling.
		document.body.className += ' ' + 'is-mobile';

		// Main dropdown menu stuff.
		// Click on a first level link.
		$dropdownTabsToggle.on('click', function(e){
			e.preventDefault(); // Don't go to the link (we'll show a menu instead)
			e.stopPropagation(); // Don't hide the menu (it'd trigger 'hide.bs.dropdown' event from bootstrap)

			let tab = $(this).data('tab-target');

			// Then display the corresponding sub-menu.
			dropdownTabShow(tab);
		});

	} else {
		// If we're not on mobile, then we use hover on the menu items to trigger.
		$dropdownTabsToggle.hover(function(){
			let tab = $(this).data('tab-target');

			// On mouse hover the tab names, style it the 'active' class.
			$dropdownTabsToggle.removeClass('active'); // First make them all inactive.
			$(this).addClass('active'); // Make active the one we want.

			// Then display the corresponding sub-menu.
			dropdownTabShow(tab);
		});
	}

	// When toggling the main dropdown, also hide the tabs.
	// Otherwise they'll be already open the next time we toggle the main dropdown.
	$('.dropdown').on('hidden.bs.dropdown', function (e) {
		dropdownTabHideAll();
	});

	// Make it so clicking anywhere in the empty space in first level dropdown
	// also hides the tabs, that way we can 'go back' to browse the first level back and forth.
	$('.nav-main ul.nav:first').on('click', function (e) {
		if ($(this).parent().hasClass('show')){
			e.stopPropagation();
		}
		dropdownTabHideAll();
	});
});
