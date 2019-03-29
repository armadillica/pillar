import { NodesBase } from "./NodesBase";
import { thenLoadVideoProgress } from '../utils';

/**
 * Create $element from a node of type asset
 * @deprecated use vue instead
 */
export class Assets extends NodesBase{
    static create$listItem(node) {
        var markIfPublic = true;
        let $card = super.create$listItem(node);
        $card.addClass('asset');

        if (node.properties && node.properties.duration){
            let $thumbnailContainer = $card.find('.js-thumbnail-container')
            let $cardDuration = $('<div class="card-label right">' + node.properties.duration + '</div>');
            $thumbnailContainer.append($cardDuration);

            /* Video progress and 'watched' label. */
            $(window).trigger('pillar:workStart');
            thenLoadVideoProgress(node._id)
                .fail(console.log)
                .then((view_progress)=>{
                    if (!view_progress) return

                    let $cardProgress = $('<div class="progress rounded-0">');
                    let $cardProgressBar = $('<div class="progress-bar">');
                    $cardProgressBar.css('width', view_progress.progress_in_percent + '%');
                    $cardProgress.append($cardProgressBar);
                    $thumbnailContainer.append($cardProgress);

                    if (view_progress.done){
                        let card_progress_done = $('<div class="card-label">WATCHED</div>');
                        $thumbnailContainer.append(card_progress_done);
                    }
                })
                .always(function() {
                    $(window).trigger('pillar:workStop');
                });
        }

        /* 'Free' ribbon for public assets. */
        if (markIfPublic && node.permissions && node.permissions.world){
            $card.addClass('free');
        }

        return $card;
    }
}
