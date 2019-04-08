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

	var project_container = document.getElementById('project-container');
	var container_offset = project_container.offsetTop;
	var container_height = window_height - container_offset.top;
	var container_height_wheader = window_height - container_offset;
	var breadcrumbs_height = $('.breadcrumbs-container').first().height();
	var window_height_minus_nav = (window_height - container_offset);

	if ($(window).width() > 768) {
		$('#project-container').css(
			{'max-height': window_height_minus_nav + 'px',
			 'height': window_height_minus_nav + 'px'}
		);

		$('#project_nav-container, #project_tree').css(
			{'max-height': (window_height_minus_nav) + 'px',
			 'height': (window_height_minus_nav) + 'px'}
		);

		if (container_height > parseInt($('#project-container').css("min-height"))) {
			if (typeof projectTree !== "undefined"){

				$(projectTree).css(
					{'max-height': container_height_wheader + 'px',
					 'height': container_height_wheader + 'px'}
				);
			}
		}

	};
};

function loadProjectSidebar(){
	var bcloud_ui = Cookies.getJSON('bcloud_ui');

	if (bcloud_ui && bcloud_ui.hide_project_sidebar) {
		hideProjectSidebar();
	} else {
		showProjectSidebar();
	};
}

function showProjectSidebar(){
	Cookies.remove('bcloud_ui', 'hide_project_sidebar');

	$('#project-container').addClass('is-sidebar-visible');
}

function hideProjectSidebar(){
	setJSONCookie('bcloud_ui', 'hide_project_sidebar', true);

	$('#project-container').removeClass('is-sidebar-visible');
}

function toggleProjectSidebar(){
	let $projectContainer = $('#project-container');

	if ($projectContainer.hasClass('is-sidebar-visible')) {
		hideProjectSidebar();
	} else {
		showProjectSidebar();
	};
}
