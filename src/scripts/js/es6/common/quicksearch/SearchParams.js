export class SearchParams {
    constructor(kwargs) {
        this.name = kwargs['name'] || '';
        this.params = kwargs['params'] || {};
    }

    setSearchWord(q) {
        this.params['q'] = q || '';
    }
    
    getParamStr() {
        return jQuery.param(this.params);
    }
}