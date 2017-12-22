/* Edit Node */


/* Move Node */
var movingMode = Cookies.getJSON('bcloud_moving_node');


function editNode(nodeId) {

	// Remove the 'n_' suffix from the id
	if (nodeId.substring(0, 2) == 'n_') {
		nodeId = nodeId.substr(2);
	}

	var url = '/nodes/' + nodeId + '/edit?embed=1';
	$.get(url, function(dataHtml) {
		// Update the DOM injecting the generate HTML into the page
		$('#project_context').html(dataHtml);
		updateUi(nodeId, 'edit');
	})
	.fail(function(dataResponse) {
		$('#project_context').html($('<iframe id="server_error"/>'));
		$('#server_error').attr('src', url);
	})
	.always(function(){
		$('.button-edit-icon').addClass('pi-edit').removeClass('pi-spin spin');
	});
}


/* Add Node */
function addNode(nodeTypeName, parentId) {
	var url = '/nodes/create';
	var node_props = {node_type_name: nodeTypeName, project_id: ProjectUtils.projectId()};
	if (typeof(parentId) != 'undefined') {node_props.parent_id = parentId};
	$.post(url, node_props)
		.done(function(data) {
			editNode(data.data.asset_id);
	})
	.always(function(){
		$('.button-add-group-icon').addClass('pi-collection-plus').removeClass('pi-spin spin');
	})
	.fail(function(data){
		toastr.error(data.status + ' - ' + data.statusText, 'Error creating node');
	});
}


/* Edit Button */
$('#item_edit').click(function(e){
	$('.button-edit-icon').addClass('pi-spin spin').removeClass('pi-edit');
	// When clicking on the edit icon, embed the edit
	e.preventDefault();
	if (ProjectUtils.isProject()) {
		window.location.replace(urlProjectEdit);
	} else {
		editNode(ProjectUtils.nodeId());
	}
});


function moveModeEnter() {
	$('#overlay-mode-move-container').addClass('visible');
	$('.button-move').addClass('disabled');

	// Scroll to top so we can see the instructions/buttons
	$("#project_context-container").scrollTop(0);
}

function moveModeExit() {
	/* Remove cookie, display current node, remove UI */
	if (ProjectUtils.isProject()) {
		displayProject(ProjectUtils.projectId());
	} else {
		displayNode(ProjectUtils.nodeId());
	}
	$('#overlay-mode-move-container').removeClass('visible');
	$('.button-move').removeClass('disabled');
	$('#item_move_accept').html('<i class="pi-check"></i> Move Here');
	Cookies.remove('bcloud_moving_node');
}


$( document ).ready(function() {
	if (movingMode) {
		moveModeEnter();
	} else {
		$('#overlay-mode-move-container').removeClass('visible');
		$('.button-move').removeClass('disabled');
	}

	/* Add Node Type Button */
	$('.item_add_node').click(function(e){
		e.preventDefault();
		var nodeTypeName = $(this).data('node-type-name');
		if (ProjectUtils.isProject()) {
			addNode(nodeTypeName);
		} else {
			addNode(nodeTypeName, ProjectUtils.nodeId());
		}
	});

	$('#item_move').click(function(e){
		e.preventDefault();
		moveModeEnter();
		// Set the nodeId in the cookie
		Cookies.set('bcloud_moving_node', { node_id: ProjectUtils.nodeId(), node_type: ProjectUtils.nodeType()});
	});

	$("#item_move_accept").click(function(e) {
		e.preventDefault();
		var movingNodeId = Cookies.getJSON('bcloud_moving_node').node_id;
		var moveNodeParams = {node_id: movingNodeId};
		// If we are not at the root of the project, add the parent node id to the
		// request params
		if (!ProjectUtils.isProject()) {
			moveNodeParams.dest_parent_node_id = ProjectUtils.nodeId();
		}

		$(this).html('<i class="pi-spin spin"></i> Moving...');

		$.post(urlNodeMove, moveNodeParams,
			function(data){
		}).done(function() {
			toastr.success('Moved!');
			Cookies.remove('bcloud_moving_node');
			moveModeExit();
			$('#project_tree').jstree("refresh");
		})
		.fail(function(data){
			toastr.error(data.status + ' - ' + data.statusText, 'Error moving node');
			$(this).html('<i class="pi-check"></i> Move Here');
		});
	});

	$("#item_move_cancel").click(function(e) {
		e.preventDefault();
		$('.button-edit-icon').addClass('pi-spin spin').removeClass('pi-cancel');

		moveModeExit();
	});


	/* Featured Toggle */
	$('#item_featured').click(function(e){
		e.preventDefault();
		$.post(urlNodeFeature, {node_id : ProjectUtils.nodeId()},
			function(data){
			// Feedback logic
		})
		.done(function(){
			toastr.success('Featured status toggled');
		})
		.fail(function(data){
			toastr.error(data.status + ' - ' + data.statusText, 'Error toggling featured status');
		});
	});


	/* Project Header toggle */
	$('#item_toggle_projheader').click(function (e) {
		e.preventDefault();

		$.post(urlNodeToggleProjHeader, {node_id: ProjectUtils.nodeId()})
			.done(function (data) {
				toastr.success('Project header ' + data.action + '!');
			})
			.fail(function (jsxhr) {
				var content_type = jsxhr.getResponseHeader('Content-Type');

				if(content_type.startsWith('application/json')) {
					var data = jsxhr.responseJSON;
					toastr.error(data.message, 'Error toggling header');
				} else {
					toastr.error(jsxhr.responseText, 'Error toggling header');
				}
			});
	});


	/* Delete */
	$('#item_delete').click(function(e){
		e.preventDefault();
		if (ProjectUtils.isProject()) {
			$.post(urlProjectDelete, {project_id: ProjectUtils.projectId()},
				function (data) {
					// Feedback logic
				}).done(function () {
					window.location.replace('/p/');
			});
		} else {
			$.post(urlNodeDelete, {node_id: ProjectUtils.nodeId()},
				function (data) {
					// Feedback logic
				})
				.done(function () {
					toastr.success('Deleted!');

					if (ProjectUtils.parentNodeId() != '') {
						displayNode(ProjectUtils.parentNodeId());
					} else {
						// Display the project when the group is at the root of the tree
						displayProject(ProjectUtils.projectId());
					}

					setTimeout(function(){
						$('#project_tree').jstree('refresh');
					}, 1000);

				})
				.fail(function (data) {
					toastr.error(data.status + ' - ' + data.statusText, 'Error deleting');
				});
		}
	});


	/* Toggle public */
	$('#item_toggle_public').click(function(e){
		e.preventDefault();
		var currentNodeId = ProjectUtils.nodeId();
		$.post(urlNodeTogglePublic, {node_id : currentNodeId},
			function(data){
			// Feedback logic
		})
		.done(function(data){
			toastr.success(data.data.message);
			displayNode(currentNodeId);
		})
		.fail(function(data){
			toastr.error(data.status + ' - ' + data.statusText, 'Error toggling status');
		});
	});

	$('ul.project-edit-tools').removeClass('disabled');
});
