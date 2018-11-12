import { NodesFactoryInterface } from './nodes'
import { thenLoadImage, thenLoadVideoProgress } from './utils';

class Assets extends NodesFactoryInterface{
    static create$listItem(node) {
        var markIfPublic = true;
        let $card = $('<a class="card asset card-image-fade pr-0 mx-0 mb-2">')
            .addClass('js-tagged-asset')
            .attr('href', '/nodes/' + node._id + '/redir')
            .attr('title', node.name);
    
        let $thumbnailContainer = $('<div class="embed-responsive embed-responsive-16by9">');
    
        function warnNoPicture() {
            let $cardIcon = $('<div class="card-img-top card-icon embed-responsive-item">');
            $cardIcon.html('<i class="pi-' + node.node_type + '">');
            $thumbnailContainer.append($cardIcon);
        }
    
        if (!node.picture) {
            warnNoPicture();
        } else {
            $(window).trigger('pillar:workStart');
    
            thenLoadImage(node.picture)
                .fail(warnNoPicture)
                .then((imgVariation)=>{
                    let img = $('<img class="card-img-top embed-responsive-item">')
                        .attr('alt', node.name)
                        .attr('src', imgVariation.link)
                        .attr('width', imgVariation.width)
                        .attr('height', imgVariation.height);
                    $thumbnailContainer.append(img);
                })
                .always(function(){
                    $(window).trigger('pillar:workStop');
                });
        }
    
        $card.append($thumbnailContainer);
    
        /* Card body for title and meta info. */
        let $cardBody = $('<div class="card-body py-2 d-flex flex-column">');
        let $cardTitle = $('<div class="card-title mb-1 font-weight-bold">');
        $cardTitle.text(node.name);
        $cardBody.append($cardTitle);
    
        let $cardMeta = $('<ul class="card-text list-unstyled d-flex text-black-50 mt-auto">');
        let $cardProject = $('<a class="font-weight-bold pr-2">')
            .attr('href', '/p/' + node.project.url)
            .attr('title', node.project.name)
            .text(node.project.name);
    
        $cardMeta.append($cardProject);
        $cardMeta.append('<li>' + node.pretty_created + '</li>');
        $cardBody.append($cardMeta);
    
        if (node.properties.duration){
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
    
        $card.append($cardBody);
    
        return $card;
    }
}


export { Assets };