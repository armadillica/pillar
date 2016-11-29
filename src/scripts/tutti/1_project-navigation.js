function projectNavCollapse() {

	$("#project-side-container").addClass('collapsed');
	$("ul.breadcrumb.context").addClass('active');
};

function projectNavExpand() {

	$("#project-side-container").removeClass('collapsed');
	$("ul.breadcrumb.context").removeAttr('class');
};

function projectNavCheck(){

	/* Only run if there is a tree */
	if(document.getElementById("project_tree") !== null) {

		var nav_status = Cookies.getJSON('bcloud_ui');

		if (nav_status && nav_status.nav_collapsed) {
			if (nav_status.nav_collapsed == 'expanded') {
				projectNavExpand();

			} else if ( nav_status.nav_collapsed == 'collapsed' ) {
				projectNavCollapse();
			}
		} else {
			projectNavExpand();
		}

	}
}

function projectNavToggle(){

	var nav_status = Cookies.getJSON('bcloud_ui');

	if (nav_status && nav_status.nav_collapsed) {
		if (nav_status.nav_collapsed == 'expanded') {

			projectNavCollapse();
			setJSONCookie('bcloud_ui', 'nav_collapsed', 'collapsed');

		} else if ( nav_status.nav_collapsed == 'collapsed' ) {

			projectNavExpand();
			setJSONCookie('bcloud_ui', 'nav_collapsed', 'expanded');

		}
	} else {
		projectNavCollapse();
		setJSONCookie('bcloud_ui', 'nav_collapsed', 'collapsed');
	}

	$('#project_context-header').width($('#project_context-container').width());
}

$(function () {

	/* Check on first load */
	projectNavCheck();

	$('.project_split, .project_nav-toggle-btn').on('click', function (e) {
		projectNavToggle();
	});

	/* Only run if there is a tree */
	if(document.getElementById("project_tree") !== null) {

		$(document).keypress(function(e) {
			var tag = e.target.tagName.toLowerCase();

			/* Toggle when pressing [T] key */
			if(e.which == 116 && tag != 'input' && tag != 'textarea' && !e.ctrlKey && !e.metaKey && !e.altKey) {
				projectNavToggle();
			}
		});
	}

});


/* Small utility to enable specific node_types under the Add New dropdown */
/* It takes:
	 * empty: Enable every item
	 * false: Disable every item
	 * array: Disable every item except a list of node_types, e.g: ['asset', 'group']
*/
function addMenuEnable(node_types){
	$("#item_add").parent().removeClass('disabled');
	$("ul.add_new-menu li[class^='button-']").hide().addClass('disabled');

	if (node_types === undefined) {
		$("ul.add_new-menu li[class^='button-']").show().removeClass('disabled');
	} else if (node_types == false) {
		$("#item_add").parent().addClass('disabled');
	} else {
		$.each(node_types, function(index, value) {
			$("ul.add_new-menu li[class*='button-" + value +"']").show().removeClass('disabled');
		});
	}
}

function addMenuDisable(node_types){
	$.each(node_types, function(index, value) {
		$("ul.add_new-menu li[class*='button-" + value +"']").addClass('disabled');
	});
}

/* Completely hide specific items (like Texture when on project root) */
function addMenuHide(node_types){
	$.each(node_types, function(index, value) {
		$("ul.add_new-menu li[class*='button-" + value +"']").hide().addClass('disabled');
	});
}

/* Jump to the top of the page! */
function hopToTop(limit){
	if (limit == null) {
		limit = 500;
	}

	document.getElementById("hop").onclick = function(e){ window.scrollTo(0, 0);}

	$(window).on("scroll", function () {
		if ($(window).scrollTop() >= limit) {$("#hop").addClass("active")} else {$("#hop").removeAttr("class")}
	});
}


/* Utility to replace a single item on a JSON cookie  */
function setJSONCookie(cookieToChange, cookieItem, cookieData){

	/* Get cookie to change, and its list if it has any */
	var cookieList = Cookies.getJSON(cookieToChange);

	/* Create an empty list if there's no cookie */
	if (!cookieList){ cookieList = {}; }

	cookieList[cookieItem] = cookieData;

	/* Set (or create) cookie */
	Cookies.set(cookieToChange, cookieList);
}


function containerResizeY(window_height){

	var container_offset = $('#project-container').offset();
	var container_height = window_height - container_offset.top;
	var container_height_wheader = window_height - container_offset.top - $('#project_nav-header').height();
	var window_height_minus_nav = window_height - $('#project_nav-header').height() - 50; // 50 is global top navbar

	$('#project_context-header').width($('#project_context-container').width());

	if ($(window).width() > 768) {
		$('#project_nav-container, #project_tree, .project_split').css(
			{'max-height': window_height_minus_nav + 'px',
			 'height': window_height_minus_nav + 'px'}
		);

		if (container_height > parseInt($('#project-container').css("min-height"))) {
			if (projectTree){
				$(projectTree).css(
					{'max-height': container_height_wheader + 'px',
					 'height': container_height_wheader + 'px'}
				);
			}
		}

	};
};
