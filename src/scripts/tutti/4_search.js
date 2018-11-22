/*
* == Search ==
* index and algolia settings are defined in layout.pug
*/

var elasticSearcher = (function() {

  var deze = {

    query:"",
    project_id:"",
    url:"",
    newhits: [],
    terms: {},
    page: 0,
    last_query: null,  // to prevent re-querying for the same thing.

    setQuery: (function(q, _url){
      deze.query=q;
      if (_url !== undefined) {
        deze.url=_url;
      }
    }),

    setProjectID: (function(pid){
      deze.project_id = pid;
    }),

    setCurrentPage: (function(page){
      if(page === undefined){
        return;
      }
      deze.page = page;
    }),

    //result callback
    results: (function(content){}),

    //error callback
    error: (function(message){
      toastr.error(message);
    }),

    on: (function(type, callback){
      deze[type] = callback;
    }),

    //parse the agg stuff
    aggs: (function(data){
      return deze.newhits.aggregations;
    }),

    toggleTerm: (function(term, value){
      if (deze.terms[term] !== undefined) {
        delete deze.terms[term];
      } else {
        deze.terms[term] = value;
      }
    }),

    isRefined: (function(term, value){
      if (deze.terms[term] === value) {
        return true;
      }
      return false;
    }),

    getParams:(function(){
      var params = {
        q: deze.query,
        page: deze.page,
        project: deze.project_id,
      };
      //add term filters
      Object.assign(params, deze.terms);
      return params;
    }),

    //get response from elastic and rebuild json
    //so we  can be a drop in of angolia
    execute: (function(){
      var pstr = jQuery.param( deze.getParams() );
      if (pstr === deze.last_query) return;

      $.getJSON("/api/newsearch" + deze.url + "?"+ pstr)
      .done(function (data) {
        var hits = data.hits.hits;
        var newhits = hits.map(function(hit){
          return hit._source;
        });

        deze.newhits = newhits.slice(0);
        //cb(newhits.slice(0));
        deze.last_query = pstr;
        deze.results({
          'count': data.hits.total,
          'hits': newhits.slice(0),
          'took': data.took,
          'page': deze.page,
          'aggs': data.aggregations,
        });
      })
      .fail(function(err) {
          toastr.error(xhrErrorResponseMessage(err), 'Unable to perform search:');
          deze.last_query = null;
      })
      ;

    })

  };

  return {
    execute: deze.execute,
    on: deze.on,
    setQuery: deze.setQuery,
    setProjectID: deze.setProjectID,
    setCurrentPage: deze.setCurrentPage,
    query: deze.query,
    page: deze.page,
    toggleTerm: deze.toggleTerm,
    isRefined: deze.isRefined,
    getParams: deze.getParams,
  };

})();


var elasticSearch = (function($, url) {
  return function findMatches(q, cb, async){
    if (!cb) { return; }
    $.fn.getSearch(q, cb, async, url);
  };
});



(function( $ ){

  $.fn.getSearch = function(q, cb, async, url){

    var newhits = [];
    if(url === undefined){
      url = '';
    }

    $.getJSON("/api/newsearch" + url + "?q=" + q, function( data ) {
      var hits = data.hits.hits;
      newhits = hits.map(function(hit){
        return hit._source;
      });
      cb(newhits.slice(0));
      if(async !== undefined){
        async(newhits.slice(0));
      }
    });
  };


}(jQuery));

