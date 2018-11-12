import { NodesFactoryInterface } from './nodes'
import { thenLoadImage } from './utils';

class Posts extends NodesFactoryInterface {
    static create$item(post) {
        let content = [];
        let $title = $('<div>')
            .addClass('display-4 text-uppercase font-weight-bold')
            .text(post.name);
        content.push($title);
        let $text = $('<div>')
            .addClass('lead')
            .text(post['pretty_created']);
        content.push($text);
        let $jumbotron = $('<a>')
            .addClass('jumbotron text-white jumbotron-overlay')
            .attr('href', '/nodes/' + post._id + '/redir')
            .append(
                $('<div>')
                    .addClass('container')
                    .append(
                        $('<div>')
                            .addClass('row')
                            .append(
                                $('<div>')
                                    .addClass('col-md-9')
                                    .append(content)
                            )
                    )
            );
        thenLoadImage(post.picture, 'l')
            .then((img)=>{
                $jumbotron.attr('style', 'background-image: url(' + img.link + ');')
            })
            .fail((error)=>{
                let msg = xhrErrorResponseMessage(error);
                console.log(msg || error);
            })
        let $post = $('<div>')
                .addClass('expand-image-links imgs-fluid')
                .append(
                    $jumbotron,
                    $('<div>')
                        .addClass('node-details-description mx-auto py-5')
                        .html(post['properties']['_content_html'])
                );
        
        return $post;
    }
}

export { Posts };