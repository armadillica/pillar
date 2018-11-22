import { NodesFactoryInterface } from './nodes'

class Posts extends NodesFactoryInterface {
    static create$item(post) {
        let content = [];
        let $title = $('<a>')
            .attr('href', '/nodes/' + post._id + '/redir')
            .addClass('h2 text-uppercase font-weight-bold d-block pb-3')
            .text(post.name);
        content.push($title);
        let $post = $('<div>')
                .addClass('expand-image-links imgs-fluid')
                .append(
                    content,
                    $('<div>')
                        .addClass('node-details-description mx-auto')
                        .html(post['properties']['pretty_content'])
                );

        return $post;
    }
}

export { Posts };
