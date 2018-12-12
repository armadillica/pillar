import { prettyDate } from '../../utils/prettydate';
import { thenLoadImage } from '../utils';
import { ComponentCreatorInterface } from '../component/ComponentCreatorInterface'

export class NodesBase extends ComponentCreatorInterface {
    static create$listItem(node) {
        let nid = (node._id || node.objectID); // To support both mongo and elastic nodes
        let $card = $('<a class="card node card-image-fade asset">')
            .attr('data-node-id', nid)
            .attr('href', '/nodes/' + nid + '/redir')
            .attr('title', node.name);
        let $thumbnailContainer = $('<div class="card-thumbnail js-thumbnail-container">');
        function warnNoPicture() {
            let $cardIcon = $('<div class="card-img-top card-icon">');
            $cardIcon.html('<i class="pi-' + node.node_type + '">');
            $thumbnailContainer.append($cardIcon);
        }
        if (!node.picture) {
            warnNoPicture();
        }
        else {
            $(window).trigger('pillar:workStart');
            thenLoadImage(node.picture)
                .fail(warnNoPicture)
                .then((imgVariation) => {
                    let img = $('<img class="card-img-top">')
                        .attr('alt', node.name)
                        .attr('src', imgVariation.link)
                        .attr('width', imgVariation.width)
                        .attr('height', imgVariation.height);
                    $thumbnailContainer.append(img);
                })
                .always(function () {
                    $(window).trigger('pillar:workStop');
                });
        }
        $card.append($thumbnailContainer);
        /* Card body for title and meta info. */
        let $cardBody = $('<div class="card-body p-2 d-flex flex-column">');
        let $cardTitle = $('<div class="card-title px-2 mb-2 font-weight-bold">');
        $cardTitle.text(node.name);
        $cardBody.append($cardTitle);
        let $cardMeta = $('<ul class="card-text px-2 list-unstyled d-flex text-black-50 mt-auto">');
        let $cardProject = $('<a class="font-weight-bold pr-2">')
            .attr('href', '/p/' + node.project.url)
            .attr('title', node.project.name)
            .text(node.project.name);
        $cardMeta.append($cardProject);
        let created = node._created || node.created_at; // mongodb + elastic
        $cardMeta.append('<li>' + prettyDate(created) + '</li>');
        $cardBody.append($cardMeta);
        $card.append($cardBody);
        return $card;
    }

    static canCreate(candidate) {
        return !!candidate.node_type;
    }
}
