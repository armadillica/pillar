$(document).ready(function() {

    var HITS_PER_PAGE = 25;
    var MAX_VALUES_PER_FACET = 30;

    // DOM binding
    var $inputField = $('#q');
    var $hits = $('#hits');
    var $stats = $('#stats');
    var $facets = $('#facets');
    var $pagination = $('#pagination');

    // Templates binding
    var hitTemplate = Hogan.compile($('#hit-template').text());
    var statsTemplate = Hogan.compile($('#stats-template').text());
    var facetTemplate = Hogan.compile($('#facet-template').text());
    var sliderTemplate = Hogan.compile($('#slider-template').text());
    var paginationTemplate = Hogan.compile($('#pagination-template').text());

    // something elasticy!
    var search = elasticSearcher;
   //    facets: $.map(FACET_CONFIG, function(facet) {
    //        return !facet.disjunctive ? facet.name : null;
    //    }),
    //    disjunctiveFacets: $.map(FACET_CONFIG, function(facet) {
    //        return facet.disjunctive ? facet.name : null;
    //    })
    //};

    // Input binding
    $inputField.on('keyup change', function() {
        var query = $inputField.val();
	if(query === undefined) { return; }
        toggleIconEmptyInput(!query.trim());
	search.setQuery(query);
        //setURLParams(search);
	search.execute();
    }).focus();

    // AlgoliaHelper events
    //helper.on('change', function(state) {
        //setURLParams(search);
    //});

    search.on('results', function(content){
        renderStats(content);
        renderHits(content);
        renderFacets(content);
        renderPagination(content);
        bindSearchObjects();
        renderFirstHit($(hits).children('.search-hit:first'));
    });

    //});

    /***************
     * SEARCH RENDERING
     * ***********/

    function renderFirstHit(firstHit) {

        firstHit.addClass('active');
        firstHit.find('#search-loading').addClass('active');

        function done() {
            $('.search-loading').removeClass('active');
            $('#search-error').hide();
            $('#search-hit-container').show();
        }

        window.setTimeout(function() {
            // Ignore getting that first result when there is none.
            var hit_id = firstHit.attr('data-hit-id');
            if (hit_id === undefined) {
                done();
                return;
            }

            $.get('/nodes/' + hit_id + '/view', function(dataHtml) {
                    $('#search-hit-container').html(dataHtml);
                })
                .done(done)
                .fail(function(data) {
                    $('.search-loading').removeClass('active');
                    $('#search-hit-container').hide();
                    $('#search-error').show().html('Houston!\n\n' + data.status + ' ' + data.statusText);
                });
        }, 1000);
    }

    // Initial search
    initWithUrlParams();
    //helper.search();

    function convertTimestamp(timestamp) {
        var d = new Date(timestamp * 1000), // Convert the passed timestamp to milliseconds
            yyyy = d.getFullYear(),
            mm = ('0' + (d.getMonth() + 1)).slice(-2), // Months are zero based. Add leading 0.
            dd = ('0' + d.getDate()).slice(-2), // Add leading 0.
            time;

        time = dd + '/' + mm + '/' + yyyy;

        return time;
    }


    function renderStats(content) {
        var stats = {
            nbHits: numberWithDelimiter(content.count),
            processingTimeMS: content.took,
            nbHits_plural: content.nbHits !== 1
        };
        $stats.html(statsTemplate.render(stats));
    }

    function renderHits(content) {
        var hitsHtml = '';
        for (var i = 0; i < content.hits.length; ++i) {
            // console.log(content.hits[i]);
            var created = content.hits[i].created;
            if (created) {
                content.hits[i].created = convertTimestamp(created);
            }
            var updated = content.hits[i].updated;
            if (updated) {
                content.hits[i].updated = convertTimestamp(updated);
            }
            hitsHtml += hitTemplate.render(content.hits[i]);
        }
        if (content.hits.length === 0) hitsHtml = '<p id="no-hits">We didn\'t find any items. Try searching something else.</p>';
        $hits.html(hitsHtml);
    }

    function renderFacets(content) {

        // If no results
        if (content.hits.length === 0) {
            $facets.empty();
            return;
        }

		var storeValue = function (values, label){

			return function(item){
				values.push({
					facet: label,
					label: item.key,
					value: item.key,
					count: item.doc_count,
				});
			};
		};

		console.log('FACETS');
		var facets =[];
		var aggs = content.aggs;

		for (var label in aggs) {

			let values = [];

			let buckets = aggs[label].buckets;

			if (buckets.length === 0) { continue; }

			buckets.forEach(storeValue(values, label));

			facets.push({
				title: label,
				values: values.slice(0),
			});
		}

        // Display facets
        var facetsHtml = '';

        for (var indexFacet = 0; indexFacet < facets.length; ++indexFacet) {
            var facet = facets[indexFacet];
			//title, values[facet, value]
            facetsHtml += facetTemplate.render(facet);
        }

        $facets.html(facetsHtml);
    }

    function renderPagination(content) {
        // If no results
        if (content.count === 0) {
            $pagination.empty();
            return;
        }

        var maxPages = 2;
		var nbPages = content.count / HITS_PER_PAGE;

        // Process pagination
        var pages = [];
        if (content.page > maxPages) {
            pages.push({
                current: false,
                number: 1
            });
            // They don't really add much...
            // pages.push({ current: false, number: '...', disabled: true });
        }
        for (var p = content.page - maxPages; p < content.page + maxPages; ++p) {
            if (p < 0 || p >= nbPages) {
                continue;
            }
            pages.push({
                current: content.page === p,
                number: (p + 1)
            });
        }
        if (content.page + maxPages < nbPages) {
            // They don't really add much...
            // pages.push({ current: false, number: '...', disabled: true });
            pages.push({
                current: false,
                number: nbPages
            });
        }
        var pagination = {
            pages: pages,
            prev_page: (content.page > 0 ? content.page : false),
            next_page: (content.page + 1 < nbPages ? content.page + 2 : false)
        };
        // Display pagination
        $pagination.html(paginationTemplate.render(pagination));
    }


    // Event bindings
    function bindSearchObjects() {
        // Slider binding
        // $('#customerReviewCount-slider').slider().on('slideStop', function(ev) {
        //   helper.addNumericRefinement('customerReviewCount', '>=', ev.value[0]).search();
        //   helper.addNumericRefinement('customerReviewCount', '<=', ev.value[1]).search();
        // });

        // Pimp checkboxes
        // $('input[type="checkbox"]').checkbox();
    }

    // Click binding
    $(document).on('click', '.show-more, .show-less', function(e) {
        e.preventDefault();
        $(this).closest('ul').find('.show-more').toggle();
        $(this).closest('ul').find('.show-less').toggle();
        return false;
    });

    $(document).on('click', '.toggleRefine', function() {
        search.addTerm($(this).data('facet'), $(this).data('value'));
		search.execute();
        return false;
    });

    $(document).on('click', '.gotoPage', function() {
        //helper.setCurrentPage(+$(this).data('page') - 1).search();
        $("html, body").animate({
            scrollTop: 0
        }, '500', 'swing');
        return false;
    });
    $(document).on('click', '.sortBy', function() {
        $(this).closest('.btn-group').find('.sort-by').text($(this).text());
        //helper.setIndex(INDEX_NAME + $(this).data('index-suffix')).search();
        return false;
    });
    $(document).on('click', '#input-loop', function() {
        $inputField.val('').change();
    });

    // Dynamic styles
    $('#facets').on("mouseenter mouseleave", ".button-checkbox", function(e) {
        $(this).parent().find('.facet_link').toggleClass("hover");
    });
    $('#facets').on("mouseenter mouseleave", ".facet_link", function(e) {
        $(this).parent().find('.button-checkbox button.btn').toggleClass("hover");
    });


    /************
     * HELPERS
     * ***********/

    function toggleIconEmptyInput(isEmpty) {
        if (isEmpty) {
            $('#input-loop').addClass('glyphicon-loop');
            $('#input-loop').removeClass('glyphicon-remove');
        } else {
            $('#input-loop').removeClass('glyphicon-loop');
            $('#input-loop').addClass('glyphicon-remove');
        }
    }

    function numberWithDelimiter(number, delimiter) {
        number = number + '';
        delimiter = delimiter || ',';
        var split = number.split('.');
        split[0] = split[0].replace(/(\d)(?=(\d\d\d)+(?!\d))/g, '$1' + delimiter);
        return split.join('.');
    }
    var sortByCountDesc = function sortByCountDesc(a, b) {
        return b.count - a.count;
    };
    var sortByName = function sortByName(a, b) {
        return a.value.localeCompare(b.value);
    };
    var sortByRefined = function sortByRefined(sortFunction) {
        return function(a, b) {
            if (a.refined !== b.refined) {
                if (a.refined) return -1;
                if (b.refined) return 1;
            }
            return sortFunction(a, b);
        };
    };

    function initWithUrlParams() {
        var sPageURL = location.hash;
        if (!sPageURL || sPageURL.length === 0) {
            return true;
        }
        var sURLVariables = sPageURL.split('&');
        if (!sURLVariables || sURLVariables.length === 0) {
            return true;
        }
        var query = decodeURIComponent(sURLVariables[0].split('=')[1]);
        $inputField.val(query);
        search.setQuery(query);

        for (var i = 2; i < sURLVariables.length; i++) {
            var sParameterName = sURLVariables[i].split('=');
            var facet = decodeURIComponent(sParameterName[0]);
            var value = decodeURIComponent(sParameterName[1]);
            //helper.toggleRefine(facet, value, false);
        }
        // Page has to be set in the end to avoid being overwritten
        var page = decodeURIComponent(sURLVariables[1].split('=')[1]) - 1;
        search.setCurrentPage(page);

    }

    function setURLParams(state) {
        var urlParams = '?';
        var currentQuery = state.query;
        urlParams += 'q=' + encodeURIComponent(currentQuery);
        var currentPage = state.page + 1;
        urlParams += '&page=' + currentPage;

        //for (var facetRefine in state.facetsRefinements) {
        //    urlParams += '&' + encodeURIComponent(facetRefine) + '=' + encodeURIComponent(state.facetsRefinements[facetRefine]);
        //}
        //for (var disjunctiveFacetrefine in state.disjunctiveFacetsRefinements) {
        //    for (var value in state.disjunctiveFacetsRefinements[disjunctiveFacetrefine]) {
        //        urlParams += '&' + encodeURIComponent(disjunctiveFacetrefine) + '=' + encodeURIComponent(state.disjunctiveFacetsRefinements[disjunctiveFacetrefine][value]);
        //    }
        //}
        location.replace(urlParams);
    }

});
