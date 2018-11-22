/**
 * Creates the jQuery object that is rendered when nothing is found
 * @param {String} advancedUrl Url to the advanced search with the current query
 * @returns {$element} The jQuery element that is rendered wher there are no hits
 */
function create$noHits(advancedUrl) {
    return $('<div>')
        .addClass('qs-msg text-center p-3')
		.append(
            $('<div>')
                .addClass('h1 pi-displeased'),
            $('<div>')
                .addClass('h2')
                .append(
                    $('<a>')
                    .attr('href', advancedUrl)
                    .text('Advanced search')
                )
        )
}
/**
 * Creates the jQuery object that is rendered as the search input
 * @param {Dict} searches The searches dict that is passed in on construction of the Quick-Search
 * @returns {$element} The jQuery object that renders the search input components.
 */
function create$input(searches) {
    let input = $('<input>')
        .addClass('qs-input')
        .attr('type', 'search')
        .attr('autocomplete', 'off')
        .attr('spellcheck', 'false')
        .attr('autocorrect', 'false')
        .attr('placeholder', 'Search...');
    let workingSymbol = $('<i>')
        .addClass('pi-cancel qs-busy-symbol');
    let inputComponent = [input, workingSymbol];
	if (Object.keys(searches).length > 1) {
        let i = 0;
        let select = $('<select>')
        .append(
            $.map(searches, (it, value) => {
                let option = $('<option>')
                .attr('value', value)
                .text(it['name']);
                if (i === 0) {
                    option.attr('selected', 'selected');
                }
                i += 1;
                return option;
            })
        );
        inputComponent.push(select);
    }
    return inputComponent;
}

/**
 * Creates the search result
 * @param {List} results
 * @param {String} advancedUrl
 * @returns {$element} The jQuery object that is rendered as the result
 */
function create$results(results, advancedUrl) {
    let $results = results.reduce((agg, res)=> {
        if(res['result'].length) {
            agg.push(
                $('<a>')
                    .addClass('h4 mt-4 d-flex')
                    .attr('href', res['url'])
                    .text(res['name'])
            )
            agg.push(
                $('<div>')
                    .addClass('card-deck card-deck-responsive card-padless js-asset-list p-3')
                    .append(
                        ...pillar.templates.Nodes.createListOf$nodeItems(res['result'], 10, 0)
                    )
            )
        }
        return agg;
    }, [])
    $results.push(
        $('<a>')
            .attr('href', advancedUrl)
            .text('Advanced search...')
    )

    return $('<div>')
        .addClass('m-auto qs-result')
        .append(...$results)
}

export { create$noHits, create$results, create$input }
