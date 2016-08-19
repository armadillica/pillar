/*
* == Search ==
* index and algolia settings are defined in layout.jade
*/

$(document).ready(function() {
	var searchInput = $('#cloud-search');

	var tu = searchInput.typeahead({hint: true}, {
		source: index.ttAdapter(),
		displayKey: 'name',
		limit: 10,
		minLength: 0,
		templates: {
			suggestion: function(hit) {

				var hitMedia = (hit.media ? ' · <span class="media">'+hit.media+'</span>' : '');
				var hitFree = (hit.is_free ? '<div class="search-hit-ribbon"><span>free</span></div>' : '');
				var hitPicture;

				if (hit.picture){
					hitPicture = '<img src="' + hit.picture + '"/>';
				} else {
					hitPicture = '<div class="search-hit-thumbnail-icon">';
					hitPicture += (hit.media ? '<i class="pi-' + hit.media + '"></i>' : '<i class="dark pi-'+ hit.node_type + '"></i>');
					hitPicture += '</div>';
				};

				return '' +
					'<a href="/nodes/'+ hit.objectID + '/redir" class="search-site-result" id="'+ hit.objectID + '">' +
						'<div class="search-hit">' +
							'<div class="search-hit-thumbnail">' +
								hitPicture +
								hitFree +
							'</div>' +
							'<div class="search-hit-name" title="' + hit.name + '">' +
								hit._highlightResult.name.value + ' ' +
							'</div>' +
							'<div class="search-hit-meta">' +
								'<span class="project">' + hit._highlightResult.project.name.value + '</span> · ' +
								'<span class="node_type">' + hit.node_type + '</span>' +
								hitMedia +
							'</div>' +
						'</div>'+
					'</a>';
			}
		}
	});


	$('.search-site-result.advanced, .search-icon').on('click', function(e){
		e.stopPropagation();
		e.preventDefault();
		window.location.href = '/search#q='+ $("#cloud-search").val() + '&page=1';
	});


	searchInput.bind('typeahead:select', function(ev, hit) {
		$('.search-icon').removeClass('pi-search').addClass('pi-spin spin');

		window.location.href = '/nodes/'+ hit.objectID + '/redir';
	});

	searchInput.bind('typeahead:active', function() {
		$('#search-overlay').addClass('active');
		$('.page-body').addClass('blur');
	});

	searchInput.bind('typeahead:close', function() {
		$('#search-overlay').removeClass('active');
		$('.page-body').removeClass('blur');
	});

	searchInput.keyup(function(e) {
		if ( $('.tt-dataset').is(':empty') ){
			if(e.keyCode == 13){
				window.location.href = '/search#q='+ $("#cloud-search").val() + '&page=1';
			};
		};
	});

	searchInput.bind('typeahead:render', function(event, suggestions, async, dataset) {
		if( suggestions != undefined && $('.tt-all-results').length <= 0){
			$('.tt-dataset').append(
				'<a id="search-advanced" href="/search#q='+ $("#cloud-search").val() + '&page=1" class="search-site-result advanced tt-suggestion">' +
					'<div class="search-hit">' +
						'<div class="search-hit-thumbnail">' +
							'<div class="search-hit-thumbnail-icon">' +
								'<i class="pi-search"></i>' +
							'</div>' +
						'</div>' +
						'<div class="search-hit-name">' +
							'Use Advanced Search' +
						'</div>' +
					'</div>'+
				'</a>');
		};
	});

});
