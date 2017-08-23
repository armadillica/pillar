(function ( $ ) {
    // See organizations/view_embed.jade for example use.
    $.fn.userSearch = function(algolia_application_id, algolia_public_key, algolia_index_users, on_selected) {
        var client = algoliasearch(algolia_application_id, algolia_public_key);
        var index = client.initIndex(algolia_index_users);

        var target = this;
        this.autocomplete({hint: false}, [
            {
                source: function (q, cb) {
                    index.search(q, {hitsPerPage: 5}, function (error, content) {
                        if (error) {
                            cb([]);
                            return;
                        }
                        cb(content.hits, content);
                    });
                },
                displayKey: 'full_name',
                minLength: 2,
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
