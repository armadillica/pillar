import { NodesBase } from "./NodesBase";

export class Posts extends NodesBase {
    static create$item(post) {
        let content = [];
        let $title = $('<div>')
            .addClass('display-4 text-uppercase font-weight-bold')
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
