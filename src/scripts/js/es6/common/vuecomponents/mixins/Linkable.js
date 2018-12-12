/**
 * Vue mixin that scrolls element into view if id matches #value in url
 * @param {String} id identifier that is set by the user of the mixin
 * @param {Boolean} isLinked true if Component is linked
 */
let hash = window.location.hash.substr(1).split('?')[0];
var Linkable = {
    data() {
        return {
            id: '',
            isLinked: false,
        } 
    },
    mounted: function () {
        this.$nextTick(function () {
            if(hash && this.id === hash) {
                this.isLinked = true;
                this.$el.scrollIntoView({ behavior: 'smooth' });
            }
        })
      }
}

export { Linkable }