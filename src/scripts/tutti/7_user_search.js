(function ( $ ) {
    // See organizations/view_embed.pug for example use.
    $.fn.userSearch = function(on_selected) {

        var target = this;
        this.autocomplete({hint: false}, [
            {
                source: elasticSearch($, '/user'),
	  	          displayKey: 'full_name',
		        		//async: true,
                minLength: 1,
                limit: 9,
                templates: {
                    suggestion: function (hit) {
                        var suggestion = hit.full_name + ' (' + hit.username + ')';
                        var $p = $('<p>').text(suggestion);
                        return $p.html();
                    }
                }
            }
        ])
        .on('autocomplete:selected', function (event, hit, dataset) {
            on_selected(event, hit, dataset);
        })
        ;

        return this;
    };
}(jQuery));
