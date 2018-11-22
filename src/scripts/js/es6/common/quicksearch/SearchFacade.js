import {MultiSearch} from './MultiSearch';

export class SearchFacade {
    /**
     * One SearchFacade holds n-number of MultiSearch objects, and delegates search requests to the active mutlisearch
     * @param {*} kwargs 
     */
    constructor(kwargs) {
        this.searches = SearchFacade.createMultiSearches(kwargs);
        this.currentScope = 'cloud'; // which multisearch to use
        this.currRequest;
        this.resultCB;
        this.failureCB;
        this.q = '';
    }

    setSearchWord(q) {
        this.q = q;
        $.each(this.searches, (k, mSearch) => {
            mSearch.setSearchWord(q);
        });
    }

    getSearchWord() {
        return this.q;
    }

    getSearchUrl() {
        return this.searches[this.currentScope].getSearchUrl();
    }

    setCurrentScope(scope) {
        this.currentScope = scope;
    }

    execute() {
        if (this.currRequest) {
            this.currRequest.abort();
        }
        this.currRequest = this.searches[this.currentScope].thenExecute();
        this.currRequest
            .then((results) => {
                this.resultCB(results);
            })
            .fail((err, reason) => {
                if (reason == 'abort') {
                    return;
                }
                this.failureCB(err);
            });
    }

    setOnResultCB(cb) {
        this.resultCB = cb;
    }

    setOnFailureCB(cb) {
        this.failureCB = cb;
    }
    
    static createMultiSearches(kwargs) {
        var searches = {};
        $.each(kwargs, (key, value) => {
            searches[key] = new MultiSearch(value);
        });
        return searches;
    }
}