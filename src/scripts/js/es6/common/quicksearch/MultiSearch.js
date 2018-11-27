import {SearchParams} from './SearchParams';

export class MultiSearch {
    constructor(kwargs) {
        this.uiUrl = kwargs['uiUrl']; // Url for advanced search
        this.apiUrl = kwargs['apiUrl']; // Url for api calls
        this.searchParams = MultiSearch.createMultiSearchParams(kwargs['searchParams']);
        this.q = '';
    }
    
    setSearchWord(q) {
        this.q = q;
        this.searchParams.forEach((qsParam) => {
            qsParam.setSearchWord(q);
        });
    }

    getSearchUrl() {
        return this.uiUrl + '?q=' + this.q;
    }

    getAllParams() {
        let retval = $.map(this.searchParams, (msParams) => {
            return msParams.params;
        });
        return retval;
    }

    parseResult(rawResult) {
        return $.map(rawResult, (subResult, index) => {
            let name = this.searchParams[index].name;
            let pStr = this.searchParams[index].getParamStr();
            let result = $.map(subResult.hits.hits, (hit) => {
                return hit._source;
            });
            return {
                name: name,
                url: this.uiUrl + '?' + pStr,
                result: result,
                hasResults: !!result.length
            };
        });
    }

    thenExecute() {
        let data = JSON.stringify(this.getAllParams());
        let rawAjax = $.ajax({
            url: this.apiUrl,
            type: 'POST',
            data: data,
            dataType: 'json',
            contentType: 'application/json; charset=UTF-8'
        });
        let prettyPromise = rawAjax.then(this.parseResult.bind(this));
        prettyPromise['abort'] = rawAjax.abort.bind(rawAjax); // Hack to be able to abort the promise down the road
        return prettyPromise;
    }

    static createMultiSearchParams(argsList) {
        return $.map(argsList, (args) => {
            return new SearchParams(args);
        });
    }
}