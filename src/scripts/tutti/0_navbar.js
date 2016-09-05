$(function () {
	$('[data-toggle="tooltip"]').tooltip({'delay' : {'show': 1250, 'hide': 250}});
	$('[data-toggle="popover"]').popover();
})

function NavbarTransparent() {

	var startingpoint = 15;

	$(window).on("load scroll", function () {

		if ($(this).scrollTop() > startingpoint) {
			$('.navbar-overlay, .navbar-transparent').addClass('is-active');
			if(document.getElementById("project_context-header") !== null) {
				$('#project_context-header').addClass('is-offset');
			}
		} else {
			$('.navbar-overlay, .navbar-transparent').removeClass('is-active');
			if(document.getElementById("project_context-header") !== null) {
				$('#project_context-header').removeClass('is-offset');
			}
		};
	});
};

NavbarTransparent();


/* Status Bar */
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

	var text = icon + html;
	$("#project-statusbar").addClass('active ' + classes);
	$("#project-statusbar").html(text);

	/* Back to normal */
	setTimeout(function(){
	$("#project-statusbar").removeAttr('class');
	$("#project-statusbar").html();
	}, time);
};

