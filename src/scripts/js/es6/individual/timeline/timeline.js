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
const DEFAULT_URL = '/api/timeline';
const transformPlaceholder = pillar.utils.transformPlaceholder;

class Timeline {
    constructor(target, builder) {
        this._$targetDom = $(target);
        this._url;
        this._queryParams = {};
        this._builder = builder;
        this._init();
    }

    _init() {
        this._workStart();
        this._setUrl();
        this._setQueryParams();
        this._thenLoadMore()
            .then((it)=>{
                transformPlaceholder(this._$targetDom, () => {
                    this._$targetDom.empty()
                            .append(it);
                        if (this._hasMore()) {
                            let btn = this._create$LoadMoreBtn();
                            this._$targetDom.append(btn);
                        }
                })
            })
            .always(this._workStop.bind(this));
    }

    _setUrl() {
        let projectId = this._$targetDom.data('project-id');
        this._url = DEFAULT_URL
        if (projectId) {
            this._url += '/p/' + projectId
        }
    }

    _setQueryParams() {
        let sortDirection = this._$targetDom.data('sort-dir');
        if (sortDirection) {
            this._queryParams['dir'] = sortDirection;
        }
    }

    _loadMore(event) {
        let $spinner = $('<i>').addClass('ml-2 pi-spin spinner');
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
            .addClass('btn btn-outline-primary btn-block js-load-next mb-3')
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
            .addClass('group')
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
                    .addClass('card-deck card-padless card-deck-responsive js-asset-list py-3')
                    .append(pillar.templates.Nodes.createListOf$nodeItems(secondaryNodes))
            );
        }
        return content;
    }

    _create$Label(level, label, url) {
        let type = level == 0 ? 'h6 float-right py-2' : 'h6 py-2 group-title'
        if (url) {
            return $('<div>')
                .addClass(type + ' sticky-top')
                .append(
                    $('<a>')
                        .addClass('text-muted font-weight-bold')
                        .attr('href', url)
                        .text(label)
            );
        }
        return $('<div>')
            .addClass(type + ' text-secondary sticky-top')
            .text(label);
    }
 }

$.fn.extend({
    timeline: function() {
        this.each(function(i, target) {
            new Timeline(target,
                new GroupBuilder()
            );
        });
    }
})

export { Timeline };
