import { NodesBase } from "./NodesBase";

/**
 * Create $element from a node of type post
 * @deprecated use vue instead
 */
export class Posts extends NodesBase {
    static create$item(post) {
        let content = [];
        let $title = $('<a>')
            .attr('href', '/nodes/' + post._id + '/redir')
            .attr('title', post.name)
            .addClass('timeline-post-title')
            .text(post.name);
        content.push($title);
        let $post = $('<div>')
                .addClass('expand-image-links imgs-fluid')
                .append(
                    content,
                    $('<div>')
                        .addClass('node-details-description')
                        .html(post['properties']['pretty_content'])
                );

        return $post;
    }
}
