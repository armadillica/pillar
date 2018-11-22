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
    var statsTemplate = Hogan.compile($('#stats-template').text());
    var facetTemplate = Hogan.compile($('#facet-template').text());
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
        updateUrlParams();
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
            var hit_id = firstHit.attr('data-node-id');
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

    function renderStats(content) {
        var stats = {
            nbHits: numberWithDelimiter(content.count),
            processingTimeMS: content.took,
            nbHits_plural: content.nbHits !== 1
        };
        $stats.html(statsTemplate.render(stats));
    }

    function renderHits(content) {
        $hits.empty();
        if (content.hits.length === 0) {
            $hits.html('<p id="no-hits">We didn\'t find any items. Try searching something else.</p>');
        }
        else {
            listof$hits = content.hits.map(function(hit){
                return pillar.templates.Component.create$listItem(hit)
                    .addClass('js-search-hit cursor-pointer search-hit');
            })
            $hits.append(listof$hits);
        }
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
                    label: item.key_as_string || item.key,
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
                title: removeUnderscore(label),
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

    function removeUnderscore(s) {
    	return s.replace(/_/g, ' ')
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
        var pageURL = decodeURIComponent(window.location.search.substring(1)),
            urlVariables = pageURL.split('&'),
            query,
            i;
        for (i = 0; i < urlVariables.length; i++) {
            var parameterPair = urlVariables[i].split('='),
                key = parameterPair[0],
                sValue = parameterPair[1];
            if (!key) continue;
            if (key === 'q') {
                query = sValue;
                continue;
            }
            if (key === 'page') {
                var page = Number.parseInt(sValue)
                search.setCurrentPage(isNaN(page) ? 0 : page)
                continue;
            }
            if (key === 'project') {
                continue;  // We take the project from the path
            }
            if (sValue !== undefined) {
            	var iValue = Number.parseInt(sValue),
            	    value = isNaN(iValue) ? sValue : iValue;
                search.toggleTerm(key, value);
                continue;
            }
            console.log('Unhandled url parameter pair:', parameterPair)
        }
        $inputField.val(query);
        do_search(query || '');
    }

    function updateUrlParams() {
        var prevState = history.state,
            prevTitle = document.title,
            params = search.getParams(),
            newUrl = window.location.pathname + '?';
        delete params['project']  // We take the project from the path
        newUrl += jQuery.param(params)
        history.replaceState(prevState, prevTitle, newUrl);
    }
});
