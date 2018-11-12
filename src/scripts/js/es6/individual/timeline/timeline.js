/**
 * Consumes data in the form:
 * {
 *  groups: [{
 *      label: 'Week 32',
 *      url: null, // optional
 *      groups: [{
 *          label: 'Spring',
 *          url: '/p/spring',
 *          items:{
 *              post: [nodeDoc, nodeDoc],  // primary (fully rendered)
 *              asset: [nodeDoc, nodeDoc]   // secondary (rendered as list item)
 *          },
 *          groups: ...
 *      }]
 * }],
 *  continue_from: 123456.2 // python timestamp
 * }
 */

class Timeline {
    constructor(target, params, builder) {
        this._$targetDom = $(target)
        this._url = params['url'];
        this._queryParams = params['queryParams'] || {};
        this._builder = builder;
        this._init();
    }

    _init() {
        this._workStart();
        this._thenLoadMore()
            .then((it)=>{
                this._$targetDom.empty();
                this._$targetDom.append(it);
                if (this._hasMore()) {
                    let btn = this._create$LoadMoreBtn();
                    this._$targetDom.append(btn);
                }
            })
            .always(this._workStop.bind(this));
    }

    _loadMore(event) {
        let $spinner = $('<i>').addClass('pi-spin spinner');
        let $loadmoreBtn = $(event.target)
            .append($spinner)
            .addClass('disabled');

        this._workStart();
        this._thenLoadMore()
            .then((it)=>{
                $loadmoreBtn.before(it);
            })
            .always(()=>{
                if (this._hasMore()) {
                    $loadmoreBtn.removeClass('disabled');
                    $spinner.remove();
                } else {
                    $loadmoreBtn.remove();
                }
                this._workStop();
            });
    }

    _hasMore() {
        return !!this._queryParams['from'];
    }

    _thenLoadMore() {
        this._workStart();
        let qParams = $.param(this._queryParams);
        return $.getJSON(this._url + '?' + qParams)
            .then(this._render.bind(this))
            .fail(this._workFailed.bind(this))
            .always(this._workStop.bind(this))
    }

    _render(toRender) {
        this._queryParams['from'] = toRender['continue_from'];
        return toRender['groups']
            .map(this._create$Group.bind(this));
    }

    _create$Group(group) {
        return this._builder.build$Group(0, group);
    }

    _create$LoadMoreBtn() {
        return $('<a>')
            .addClass('btn btn-outline-primary js-load-next')
            .attr('href', 'javascript:void(0);')
            .click(this._loadMore.bind(this))
            .text('Load More Weeks');
    }

    _workStart() {
        this._$targetDom.trigger('pillar:workStart');
        return arguments;
    }

    _workStop() {
        this._$targetDom.trigger('pillar:workStop');
        return arguments;
    }

    _workFailed(error) {
        let msg = xhrErrorResponseMessage(error);
        this._$targetDom.trigger('pillar:failure', msg);
        return error;
    }
}

class GroupBuilder {
    build$Group(level, group) {
        let content = []
        let $label = this._create$Label(level, group['label'], group['url']);
        if (group['items']) {
            content = content.concat(this._create$Items(group['items']));
        }
        if(group['groups']) {
            content = content.concat(group['groups'].map(this.build$Group.bind(this, level+1)));
        }
        return $('<div>')
            .append(
                $label,
                content
            );
    }

    _create$Items(items) {
        let content = [];
        let primaryNodes = items['post'];
        let secondaryNodes = items['asset'];
        if (primaryNodes) {
            content.push(
                $('<div>')
                    .append(primaryNodes.map(pillar.templates.Nodes.create$item))
            );
        }
        if (secondaryNodes) {
            content.push(
                $('<div>')
                    .addClass('card-deck card-padless card-deck-responsive card-undefined-columns js-asset-list py-3')
                    .append(pillar.templates.Nodes.createListOf$nodeItems(secondaryNodes))
            );
        }
        return content;
    }

    _create$Label(level, label, url) {
        let size = level == 0 ? 'h5' : 'h6'
        if (url) {
            return $('<div>')
                .addClass(size +' sticky-top')
                .append(
                    $('<a>')
                        .addClass('text-muted')
                        .attr('href', url)
                        .text(label)
            );
        }
        return $('<div>')
            .addClass(size + ' text-muted sticky-top')
            .text(label);
    }
 }

$.fn.extend({
    timeline: function(params) {
        this.each(function(i, target) {
            new Timeline(target,
                params || {},
                new GroupBuilder()
            );
        });
    }
})

export { Timeline };