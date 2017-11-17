(function ( $ ) {
    // See organizations/view_embed.pug for example use.
    $.fn.userSearch = function(algolia_application_id, algolia_public_key, algolia_index_users, on_selected) {

        var target = this;
        this.autocomplete({hint: false}, [
            {
                source: elasticSearch($, '/user'),
	        displayKey: 'full_name',
		async: true,
                minLength: 1,
                limit: 10,
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
