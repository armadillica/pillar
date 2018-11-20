/**
 * Fade out placeholder, then call callback.
 * Note that the placeholder will not be removed, and will not be keeped hidden. The caller decides what to do with 
 * the placeholder.
 * @param {jQueryObject} $placeholder 
 * @param {callback} cb 
 */
export function transformPlaceholder($placeholder, cb) {
    $placeholder.addClass('placeholder replaced')
        .delay(250)
        .queue(()=>{
            $placeholder.removeClass('placeholder replaced');
            cb();
        })
}