$(document).ready(function() {

    /********************
     * INITIALIZATION
     * *******************/

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

    // Client initialization
    var algolia = algoliasearch(APPLICATION_ID, SEARCH_ONLY_API_KEY);

    // Helper initialization
    var params = {
        hitsPerPage: HITS_PER_PAGE,
        maxValuesPerFacet: MAX_VALUES_PER_FACET,
        facets: $.map(FACET_CONFIG, function(facet) {
            return !facet.disjunctive ? facet.name : null;
        }),
        disjunctiveFacets: $.map(FACET_CONFIG, function(facet) {
            return facet.disjunctive ? facet.name : null;
        })
    };

    // Setup the search helper
    var helper = algoliasearchHelper(algolia, INDEX_NAME, params);

    // Check if we passed hidden facets in the FACET_CONFIG
    var result = $.grep(FACET_CONFIG, function(e) {
        return e.hidden && e.hidden == true;
    });
    for (var i = 0; i < result.length; i++) {
        var f = result[i];
        helper.addFacetRefinement(f.name, f.value);
    }


    // Input binding
    $inputField.on('keyup change', function() {
        var query = $inputField.val();
        toggleIconEmptyInput(!query.trim());
        helper.setQuery(query).search();
    }).focus();

    // AlgoliaHelper events
    helper.on('change', function(state) {
        setURLParams(state);
    });
    helper.on('error', function(error) {
        console.log(error);
    });
    helper.on('result', function(content, state) {
        renderStats(content);
        renderHits(content);
        renderFacets(content, state);
        renderPagination(content);
        bindSearchObjects();

        renderFirstHit($(hits).children('.search-hit:first'));
    });

    /************
     * SEARCH
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
    };

    // Initial search
    initWithUrlParams();
    helper.search();

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
            nbHits: numberWithDelimiter(content.nbHits),
            processingTimeMS: content.processingTimeMS,
            nbHits_plural: content.nbHits !== 1
        };
        $stats.html(statsTemplate.render(stats));
    }

    function renderHits(content) {
        var hitsHtml = '';
        for (var i = 0; i < content.hits.length; ++i) {
            // console.log(content.hits[i]);
            var created = content.hits[i]['created'];
            if (created) {
                content.hits[i]['created'] = convertTimestamp(created);
            }
            var updated = content.hits[i]['updated'];
            if (updated) {
                content.hits[i]['updated'] = convertTimestamp(updated);
            }
            hitsHtml += hitTemplate.render(content.hits[i]);
        }
        if (content.hits.length === 0) hitsHtml = '<p id="no-hits">We didn\'t find any items. Try searching something else.</p>';
        $hits.html(hitsHtml);
    }

    function renderFacets(content, state) {
        // If no results
        if (content.hits.length === 0) {
            $facets.empty();
            return;
        }

        // Process facets
        var facets = [];
        for (var facetIndex = 0; facetIndex < FACET_CONFIG.length; ++facetIndex) {
            var facetParams = FACET_CONFIG[facetIndex];
            if (facetParams.hidden) {
                continue
            }
            var facetResult = content.getFacetByName(facetParams.name);
            if (facetResult) {
                var facetContent = {};
                facetContent.facet = facetParams.name;
                facetContent.title = facetParams.title;
                facetContent.type = facetParams.type;

                if (facetParams.type === 'slider') {
                    // if the facet is a slider
                    facetContent.min = facetResult.stats.min;
                    facetContent.max = facetResult.stats.max;
                    var valueMin = state.getNumericRefinement(facetParams.name, '>=') || facetResult.stats.min;
                    var valueMax = state.getNumericRefinement(facetParams.name, '<=') || facetResult.stats.max;
                    valueMin = Math.min(facetContent.max, Math.max(facetContent.min, valueMin));
                    valueMax = Math.min(facetContent.max, Math.max(facetContent.min, valueMax));
                    facetContent.values = [valueMin, valueMax];
                } else {
                    // format and sort the facet values
                    var values = [];
                    for (var v in facetResult.data) {
                        var label = '';
                        if (v === 'true') {
                            label = 'Yes';
                        } else if (v === 'false') {
                            label = 'No';
                        }
                        // Remove any underscore from the value
                        else {
                            label = v.replace(/_/g, " ");
                        }
                        values.push({
                            label: label,
                            value: v,
                            count: facetResult.data[v],
                            refined: helper.isRefined(facetParams.name, v)
                        });
                    }
                    var sortFunction = facetParams.sortFunction || sortByCountDesc;
                    if (facetParams.topListIfRefined) sortFunction = sortByRefined(sortFunction);
                    values.sort(sortFunction);

                    facetContent.values = values.slice(0, 10);
                    facetContent.has_other_values = values.length > 10;
                    facetContent.other_values = values.slice(10);
                    facetContent.disjunctive = facetParams.disjunctive;
                }
                facets.push(facetContent);
            }
        }
        // Display facets
        var facetsHtml = '';
        for (var indexFacet = 0; indexFacet < facets.length; ++indexFacet) {
            var facet = facets[indexFacet];
            if (facet.type && facet.type === 'slider') facetsHtml += sliderTemplate.render(facet);
            else facetsHtml += facetTemplate.render(facet);
        }
        $facets.html(facetsHtml);
    }

    function renderPagination(content) {
        // If no results
        if (content.hits.length === 0) {
            $pagination.empty();
            return;
        }

        var maxPages = 2;

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
            if (p < 0 || p >= content.nbPages) {
                continue;
            }
            pages.push({
                current: content.page === p,
                number: (p + 1)
            });
        }
        if (content.page + maxPages < content.nbPages) {
            // They don't really add much...
            // pages.push({ current: false, number: '...', disabled: true });
            pages.push({
                current: false,
                number: content.nbPages
            });
        }
        var pagination = {
            pages: pages,
            prev_page: (content.page > 0 ? content.page : false),
            next_page: (content.page + 1 < content.nbPages ? content.page + 2 : false)
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
        helper.toggleRefine($(this).data('facet'), $(this).data('value')).search();
        return false;
    });
    $(document).on('click', '.gotoPage', function() {
        helper.setCurrentPage(+$(this).data('page') - 1).search();
        $("html, body").animate({
            scrollTop: 0
        }, '500', 'swing');
        return false;
    });
    $(document).on('click', '.sortBy', function() {
        $(this).closest('.btn-group').find('.sort-by').text($(this).text());
        helper.setIndex(INDEX_NAME + $(this).data('index-suffix')).search();
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
        helper.setQuery(query);
        for (var i = 2; i < sURLVariables.length; i++) {
            var sParameterName = sURLVariables[i].split('=');
            var facet = decodeURIComponent(sParameterName[0]);
            var value = decodeURIComponent(sParameterName[1]);
            helper.toggleRefine(facet, value, false);
        }
        // Page has to be set in the end to avoid being overwritten
        var page = decodeURIComponent(sURLVariables[1].split('=')[1]) - 1;
        helper.setCurrentPage(page);

    }

    function setURLParams(state) {
        var urlParams = '#';
        var currentQuery = state.query;
        urlParams += 'q=' + encodeURIComponent(currentQuery);
        var currentPage = state.page + 1;
        urlParams += '&page=' + currentPage;
        for (var facetRefine in state.facetsRefinements) {
            urlParams += '&' + encodeURIComponent(facetRefine) + '=' + encodeURIComponent(state.facetsRefinements[facetRefine]);
        }
        for (var disjunctiveFacetrefine in state.disjunctiveFacetsRefinements) {
            for (var value in state.disjunctiveFacetsRefinements[disjunctiveFacetrefine]) {
                urlParams += '&' + encodeURIComponent(disjunctiveFacetrefine) + '=' + encodeURIComponent(state.disjunctiveFacetsRefinements[disjunctiveFacetrefine][value]);
            }
        }
        location.replace(urlParams);
    }

});
