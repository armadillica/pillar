
// Store the title, to later append notifications count
var page_title = document.title;

/**
 * Adds a new notification to the top of the notification list.
 */
function addNotification(no) {
	var $notifications_list = $('#notifications-list');

	// There is a notification to be shown, so remove any "no notifications yet" message.
	$notifications_list.find('li.nc-item-empty').remove();

	console.log('New notification:', no);
	return;
	//
	// // Increase the unread_new counter
	// if (!no['is_read']){ unread_new++ };
	//
	// // Check if the current item has been read, to style it
	// var is_read = no['is_read'] ? 'is_read' : '';
	//
	// var read_info = 'data-id="'+ no['_id'] + '" data-read="' + no['is_read'] + '"';
	//
	// // Notification list item
	// var content = '<li class="nc-item ' + is_read +'" data-id="'+ no['_id'] + '">';
	//
	// // User's avatar
	// content += '<div class="nc-avatar">';
	// 	content += '<img ' + read_info + ' src="' + no['username_avatar'] + '"/> ';
	// content += '</div>';
	//
	// // Text of the notification
	// content += '<div class="nc-text">';
	//
	// // Username and action
	// content += no['username'] + ' ' + no['action'] + ' ';
	//
	// // Object
	// content += '<a '+read_info+'" href="'+no['object_url']+'" class="nc-a">';
	// content += no['context_object_name'] + ' ';
	// content += '</a> ';
	//
	// // Date
	// content += '<span class="nc-date">';
	// content += '<a '+read_info+'" href="'+no['object_url']+'" class="nc-a">';
	// content += no['date'];
	// content += '</a>';
	// content += '</span>';
	//
	// // Read Toggle
	// content += '<a id="'+no['_id']+'" href="/notifications/' + no['_id'] + '/read-toggle" class="nc-button nc-read_toggle">';
	// 	if (no['is_read']){
	// 		content += '<i title="Mark as Unread" class="pi pi-circle-dot"></i>';
	// 	} else {
	// 		content += '<i title="Mark as Read" class="pi pi-circle"></i>';
	// 	};
	// content += '</a>';
	//
	// // Subscription Toggle
	// content += '<a href="/notifications/' + no['_id'] + '/subscription-toggle" class="nc-button nc-subscription_toggle">';
	// 	if (no['is_subscribed']){
	// 		content += '<i title="Turn Off Notifications" class="pi-toggle-on"></i>';
	// 	} else {
	// 		content += '<i title="Turn On Notifications" class="pi-toggle-off"></i>';
	// 	};
	// content += '</a>';
	//
	// content += '</div>';
	// content += '</li>';
	//
	// 		items.push(content);
	// 	}); // each
	//
	// 	if (unread_new > 0) {
	// 		// Set page title, display notifications and set counter
	// 		document.title = '(' + unread_new + ') ' + page_title;
	// 		$('#notifications-count').addClass('bloom');
	// 		$('#notifications-count').html('<span>' + unread_new + '</span>');
	// 		$('#notifications-toggle i').removeClass('pi-notifications-none').addClass('pi-notifications-active');
	// 	} else {
	// 		document.title = page_title;
	// 		$('#notifications-count').removeAttr('class');
	// 		$('#notifications-toggle i').removeClass('pi-notifications-active').addClass('pi-notifications-none');
	// 	};
	//
	// 	checkPopNotification(
	// 		data['items'][0]['_id'],
	// 		data['items'][0]['username'],
	// 		data['items'][0]['username_avatar'],
	// 		data['items'][0]['action'],
	// 		data['items'][0]['date'],
	// 		data['items'][0]['context_object_name'],
	// 		data['items'][0]['object_url']);
	//
	// 	// Populate the list
	// 	$('#notifications-list').html( items.join(''));
	// })
};

// Used when we click somewhere in the page
function hideNotifications(){
	$('#notifications').hide();
	$('#notifications-toggle').removeClass('active');
};

function popNotification(){

	// pop in!
	$("#notification-pop").addClass('in');

	// After 10s, add a class to make it pop out
	setTimeout(function(){
		$("#notification-pop").addClass('out');

		// And a second later, remove all classes
		setTimeout(function(){
			$("#notification-pop").removeAttr('class');
		}, 1000);

	}, 10000);

	// Set them the same so it doesn't pop up again
	unread_on_load = unread_new;
};


function checkPopNotification(id,username,username_avatar,action,date,context_object_name,object_url)
	{
		// If there's new content
		if (unread_new > unread_on_load){
			// Fill in the urls for redirect on click, and mark-read
			$("#notification-pop").attr('data-url', object_url);
			$("#notification-pop").attr('data-read-toggle', '/notifications/' + id + '/read-toggle');
			// The text in the pop
			var text = '<span class="nc-author">' + username + '</span> ';
			text += action + ' ';
			text += context_object_name + ' ';
			text += '<span class="nc-date">' + date + '</span>';

			// Fill the html
			$('#notification-pop .nc-text').html(text);
			$('#notification-pop .nc-avatar img').attr('src', username_avatar);

			// pop in!
			popNotification();
		};
	};


// Function to set #notifications flyout height and resize if needed
function notificationsResize(){
	var height = $(window).height() - 80;

	if ($('#notifications').height() > height){
		$('#notifications').css({
				'max-height' : height / 2,
				'overflow-y' : 'scroll'
			}
		);
	} else {
		$('#notifications').css({
				'max-height' : '1000%',
				'overflow-y' : 'initial'
			}
		);
	};
};


$(function() {
	// Click anywhere in the page to hide #notifications
	$(document).click(function () {
		hideNotifications();
	});
	// ...but clicking inside #notifications shouldn't hide itself
	$('#notifications').on('click', function (e) {
		e.stopPropagation();
	});

	// Toggle the #notifications flyout
	$('#notifications-toggle').on('click', function (e) {
		e.stopPropagation();

		$('#notifications').toggle();
		$(this).toggleClass("active");

		notificationsResize();

		// Hide other dropdowns
		$('nav .dropdown').removeClass('open');

		var navbarCollapse = $('nav.navbar-collapse');

		if ($(navbarCollapse).hasClass('in')){
			$(navbarCollapse).addClass('show-notifications').removeClass('in');
			$('.nav-notifications-icon').removeClass('pi-notifications-none').addClass('pi-cancel');
		} else {
			$(navbarCollapse).removeClass('show-notifications');
			$('.nav-notifications-icon').addClass('pi-notifications-none').removeClass('pi-cancel');
		}
	});

	// Hide flyout when clicking other dropdowns
	$('nav').on('click', '.dropdown', function (e) {
		$('#notifications').hide();
		$('#notifications-toggle').removeClass('active');
	});


	$('#notification-pop').on('click', function (e) {
		e.preventDefault();
		e.stopPropagation();

		var link_url = $(this).data('url');
		var read_url = $(this).data('read-toggle');

		$.get(read_url)
			.done(function () {
				window.location.href = link_url;
			});
	});


	// Read/Subscription Toggles
	$('ul#notifications-list').on('click', '.nc-button', function (e) {
		e.preventDefault();
		var nc = $(this);

		// Swap to spin icon while we wait for the response
		$('i', nc).addClass('spin');

		$.get($(nc).attr('href'))
			.done(function (data) {

				if ($(nc).hasClass('nc-read_toggle')) {
					if (data.data.is_read) {
						$('i', nc).removeClass('pi-circle').addClass('pi-circle-dot');
						$(nc).closest('.nc-item').addClass('is_read');
					} else {
						$('i', nc).removeClass('pi-circle-dot').addClass('pi-circle');
						$(nc).closest('.nc-item').removeClass('is_read');
					}
				}
				;

				if ($(nc).hasClass('nc-subscription_toggle')) {
					if (data.data.is_subscribed) {
						$('i', nc).removeClass('pi-toggle-on').addClass('pi-toggle-off');
					} else {
						$('i', nc).removeClass('pi-toggle-off').addClass('pi-toggle-on');
					}
				}
				;

				$('i', nc).removeClass('spin');
			});
	});


	// When clicking on links, toggle as read
	$('ul#notifications-list').on('click', '.nc-a', function (e) {
		e.preventDefault();

		var is_read = $(this).data('read');
		var link_url = $(this).attr('href');
		var read_url = '/notifications/' + $(this).data('id') + '/read-toggle';

		if (is_read) {
			window.location.href = link_url;
		} else {
			$.get(read_url)
				.done(function () {
					window.location.href = link_url;
				});
		}

	});


	// Mark All as Read
	$('#notifications-markallread').on('click', function (e) {
		e.preventDefault();

		$.get("/notifications/read-all");

		$('ul#notifications-list li.nc-item:not(.is_read)').each(function () {
			$(this).addClass('is_read');
		});

		document.title = page_title;
		$('#notifications-count').removeAttr('class');
		$('#notifications-toggle i').removeClass('pi-notifications-active').addClass('pi-notifications-none');

		unread_on_load = unread_new;
	});
});

/**
 * Uses ServerSide Events (SSE) to fetch notifications from Pillar-Notifserv.
 */
function setupNotifications() {
	var source = new EventSource('/notifications', {withCredentials: true});
    source.addEventListener('notification', function (event) {
        var notif = JSON.parse(event.data);
		addNotification(notif);
    }, false);
}
