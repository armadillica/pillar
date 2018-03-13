$(document).ready(function() {
    var HITS_PER_PAGE = 10;
    var MAX_VALUES_PER_FACET = 30;

    // DOM binding
    var $inputField = $('#q');
    var $hits = $('#hits');
    var $stats = $('#stats');
    var $facets = $('#facets');
    var $pagination = $('#pagination');
    var what = '';

    // Templates binding
    var hitTemplate = Hogan.compile($('#hit-template').text());
    var statsTemplate = Hogan.compile($('#stats-template').text());
    var facetTemplate = Hogan.compile($('#facet-template').text());
    var sliderTemplate = Hogan.compile($('#slider-template').text());
    var paginationTemplate = Hogan.compile($('#pagination-template').text());

    // defined in tutti/4_search.js
    var search = elasticSearcher;

    // what are we looking for? users? assets (default)
    what = $inputField.attr('what');

    function do_search(query) {
        if (query === undefined) {
            return;
        }
        toggleIconEmptyInput(!query.trim());

        search.setQuery(query, what);  // what could be like "/users"
        var pid = ProjectUtils.projectId();
        if (pid) search.setProjectID(pid);
        search.execute();
    }

    // Input binding
    $inputField.on('keyup change', function() {
        var query = $inputField.val();
        do_search(query);
    }).focus();

    search.on('results', function(content) {
        renderStats(content);
        renderHits(content);
        renderFacets(content);
        renderPagination(content);
        renderFirstHit($(hits).children('.search-hit:first'));
    });

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

    function convertTimestamp(iso8601) {
        var d = new Date(iso8601)
        return d.toLocaleDateString();
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
            var created = content.hits[i].created_at;
            if (created) {
                content.hits[i].created_at = convertTimestamp(created);
            }
            var updated = content.hits[i].updated_at;
            if (updated) {
                content.hits[i].updated_at = convertTimestamp(updated);
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
            facets = [];
            return;
        }

        var storeValue = function(values, label) {
            return function(item) {
                var refined = search.isRefined(label, item.key);
                values.push({
                    facet: label,
                    label: item.key,
                    value: item.key,
                    count: item.doc_count,
                    refined: refined,
                });
            };
        };

        var facets = [];
        var aggs = content.aggs;
        for (var label in aggs) {
            var values = [];
            var buckets = aggs[label].buckets;

            if (buckets.length === 0) {
                continue;
            }

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

        var maxPages = 3;
        var nbPages = Math.floor(content.count / HITS_PER_PAGE);

        // Process pagination
        var pages = [];
        if (content.page > maxPages) {
            pages.push({
                current: false,
                number: 0,
                shownr: 1
            });
        }
        for (var p = content.page - maxPages; p < content.page + maxPages; ++p) {
            if (p < 0 || p > nbPages) {
                continue;
            }
            pages.push({
                current: content.page === p,
                number: p,
                shownr: p+1
            });
        }
        if (content.page + maxPages < nbPages) {
            pages.push({
                current: false,
                number: nbPages-1,
                shownr: nbPages
            });
        }
        var pagination = {
            pages: pages,
        };
        if (content.page > 0) {
            pagination.prev_page = {page: content.page - 1};
        }
        if (content.page < nbPages) {
            pagination.next_page = {page: content.page + 1};
        }
        // Display pagination
        $pagination.html(paginationTemplate.render(pagination));
    }


    // Event bindings
    // Click binding
    $(document).on('click', '.show-more, .show-less', function(e) {
        e.preventDefault();
        $(this).closest('ul').find('.show-more').toggle();
        $(this).closest('ul').find('.show-less').toggle();
        return false;
    });

    $(document).on('click', '.toggleRefine', function() {
        search.toggleTerm($(this).data('facet'), $(this).data('value'));
        search.execute();
        return false;
    });

    $(document).on('click', '.gotoPage', function() {
        const page_idx = $(this).data('page');
        search.setCurrentPage(page_idx);
        search.execute();

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
        search.setQuery(query, what);

        for (var i = 2; i < sURLVariables.length; i++) {
            var sParameterName = sURLVariables[i].split('=');
            var facet = decodeURIComponent(sParameterName[0]);
            var value = decodeURIComponent(sParameterName[1]);
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
        location.replace(urlParams);
    }

    // do empty search to fill aggregations
    do_search('');
});
