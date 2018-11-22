import { NodesBase } from "./NodesBase";

export class Posts extends NodesBase {
    static create$item(post) {
        let content = [];
        let $title = $('<div>')
            .addClass('h1 text-uppercase mt-4 mb-3')
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
