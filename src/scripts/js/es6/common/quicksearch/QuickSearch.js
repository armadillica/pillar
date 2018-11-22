import { create$noHits, create$results, create$input } from './templates'
import {SearchFacade} from './SearchFacade';
/**
 *  QuickSearch             : Interacts with the dom document
 *    1-SearchFacade        : Controls which multisearch is active
 *      *-MultiSearch       : One multi search is typically Project or Cloud
 *        *-SearchParams    : The search params for the individual searches
 */

export class QuickSearch {
    /**
     * Interacts with the dom document and deligates the input down to the SearchFacade
     * @param {selector string} searchToggle The quick-search toggle
     * @param {*} kwargs 
     */
    constructor(searchToggle, kwargs) {
        this.$body = $('body');
        this.$quickSearch = $('.quick-search');
        this.$inputComponent = $(kwargs['inputTarget']);
        this.$inputComponent.empty();
        this.$inputComponent.append(create$input(kwargs['searches']));
        this.$searchInput = this.$inputComponent.find('input');
        this.$searchSelect = this.$inputComponent.find('select');
        this.$resultTarget = $(kwargs['resultTarget']);
        this.$searchSymbol = this.$inputComponent.find('.qs-busy-symbol');
        this.searchFacade = new SearchFacade(kwargs['searches'] || {});
        this.$searchToggle = $(searchToggle);
        this.isBusy = false;
        this.attach();
    }

    attach() {
        if (this.$searchSelect.length) {
            this.$searchSelect
                .change(this.execute.bind(this))
                .change(() => this.$searchInput.focus());
            this.$searchInput.addClass('multi-scope');
        }

        this.$searchInput
            .keyup(this.onInputKeyUp.bind(this));

        this.$inputComponent
            .on('pillar:workStart', () => {
                this.$searchSymbol.addClass('spinner')
                this.$searchSymbol.toggleClass('pi-spin pi-cancel')
            })
            .on('pillar:workStop', () => {
                this.$searchSymbol.removeClass('spinner')
                this.$searchSymbol.toggleClass('pi-spin pi-cancel')
            });

        this.searchFacade.setOnResultCB(this.renderResult.bind(this));
        this.searchFacade.setOnFailureCB(this.onSearchFailed.bind(this));
        this.$searchToggle
            .one('click', this.execute.bind(this));  // Initial search executed once
            
        this.registerShowGui();
        this.registerHideGui();
    }

    registerShowGui() {
        this.$searchToggle
            .click((e) => {
                this.showGUI();
                e.stopPropagation();
            });
    }

    registerHideGui() {
        this.$searchSymbol
            .click(() => {
                this.hideGUI();
            });
        this.$body.click((e) => {
            let $target = $(e.target);
            let isClickInResult = $target.hasClass('.qs-result') || !!$target.parents('.qs-result').length;
            let isClickInInput = $target.hasClass('.qs-input') || !!$target.parents('.qs-input').length;
            if (!isClickInResult && !isClickInInput) {
                this.hideGUI();
            }
        });
        $(document).keyup((e) => {
            if (e.key === 'Escape') {
                this.hideGUI();
            }
        });
    }

    showGUI() {
        this.$body.addClass('has-overlay');
        this.$quickSearch.trigger('pillar:searchShow');
        this.$quickSearch.addClass('show');
        if (!this.$searchInput.is(':focus')) {
            this.$searchInput.focus();
        }
    }

    hideGUI() {
        this.$body.removeClass('has-overlay');
        this.$searchToggle.addClass('pi-search');
        this.$searchInput.blur();
        this.$quickSearch.removeClass('show');
        this.$quickSearch.trigger('pillar:searchHidden');
    }

    onInputKeyUp(e) {
        let newQ = this.$searchInput.val();
        let currQ = this.searchFacade.getSearchWord();
        this.searchFacade.setSearchWord(newQ);
        let searchUrl = this.searchFacade.getSearchUrl();
        if (e.key === 'Enter') {
            window.location.href = searchUrl;
            return;
        }
        if (newQ !== currQ) {
            this.execute();
        }
    }

    execute() {
        this.busy(true);
        let scope = this.getScope();
        this.searchFacade.setCurrentScope(scope);
        let q = this.$searchInput.val();
        this.searchFacade.setSearchWord(q);
        this.searchFacade.execute();
    }

    renderResult(results) {
        this.$resultTarget.empty();
        this.$resultTarget.append(this.create$result(results));
        this.busy(false);
    }

    create$result(results) {
        let withHits = results.reduce((aggr, subResult) => {
            if (subResult.hasResults) {
                aggr.push(subResult);
            }
            return aggr;
        }, []);

        if (!withHits.length) {
            return create$noHits(this.searchFacade.getSearchUrl());
        }
        return create$results(results, this.searchFacade.getSearchUrl());
    }

    onSearchFailed(err) {
        toastr.error(xhrErrorResponseMessage(err), 'Unable to perform search:');
        this.busy(false);
        this.$inputComponent.trigger('pillar:failed', err);
    }

    getScope() {
        return !!this.$searchSelect.length ? this.$searchSelect.val() : 'cloud';
    }

    busy(val) {
        if (val !== this.isBusy) {
            var eventType = val ? 'pillar:workStart' : 'pillar:workStop';
            this.$inputComponent.trigger(eventType);
        }
        this.isBusy = val;
    }
}

$.fn.extend({
    /**
     * $('#qs-toggle').quickSearch({
     *          resultTarget: '#search-overlay',
     *          inputTarget: '#qs-input',
     *          searches: {
     *          project: {
     *              name: 'Project', 
     *              uiUrl: '{{ url_for("projects.search", project_url=project.url)}}',
     *              apiUrl: '/api/newsearch/multisearch',
     *              searchParams: [
     *                  {name: 'Assets', params: {project: '{{ project._id }}', node_type: 'asset'}},
     *                  {name: 'Blog', params: {project: '{{ project._id }}', node_type: 'post'}},
     *                  {name: 'Groups', params: {project: '{{ project._id }}', node_type: 'group'}},
     *              ]
     *          },
     *          cloud: {
     *              name: 'Cloud',
     *              uiUrl: '/search',
     *              apiUrl: '/api/newsearch/multisearch',
     *              searchParams: [
     *                  {name: 'Assets', params: {node_type: 'asset'}},
     *                  {name: 'Blog', params: {node_type: 'post'}},
     *                  {name: 'Groups', params: {node_type: 'group'}},
     *              ]
     *          },
     *      },
     *  });
     * @param {*} kwargs 
     */
    quickSearch: function (kwargs) {
        $(this).each((i, qsElem) => {
            new QuickSearch(qsElem, kwargs);
        });
    }
})