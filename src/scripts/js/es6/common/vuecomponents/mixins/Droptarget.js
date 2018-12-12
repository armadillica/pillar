/**
 * Vue mixin that makes the component a droptarget
 * override canHandleDrop(event) and onDrop(event)
 * dragOverClasses can be bound to target class
 */

var Droptarget = {
    data() {
        return {
            droptargetCounter: 0,
            droptargetCanHandle: false
        } 
    },
    computed: {
        isDragingOver() {
            return this.droptargetCounter > 0;
        },
        dropTargetClasses() {
            return {
                'drag-hover': this.isDragingOver,
                'unsupported-drop': this.isDragingOver && !this.droptargetCanHandle
            }
        }
    },
    mounted() {
        this.$nextTick(function () {
            this.$el.addEventListener('dragenter', this._onDragEnter);
            this.$el.addEventListener('dragleave', this._onDragLeave);
            this.$el.addEventListener('dragend', this._onDragEnd);
            this.$el.addEventListener('dragover', this._onDragOver);
            this.$el.addEventListener('drop', this._onDrop);
        });
    },
    beforeDestroy() {
        this.$el.removeEventListener('dragenter', this._onDragEnter);
        this.$el.removeEventListener('dragleave', this._onDragLeave);
        this.$el.removeEventListener('dragend', this._onDragEnd);
        this.$el.removeEventListener('dragover', this._onDragOver);
        this.$el.removeEventListener('drop', this._onDrop);
    },
    methods: {
        canHandleDrop(event) {
            throw Error('Not implemented');
        },
        onDrop(event) {
            throw Error('Not implemented');
        },
        _onDragEnter(event) {
            event.preventDefault();
            event.stopPropagation();
            this.droptargetCounter++;
            if(this.droptargetCounter === 1) {
                try {
                    this.droptargetCanHandle = this.canHandleDrop(event);
                } catch (error) {
                    console.warn(error);
                    this.droptargetCanHandle = false;
                }
            }
        },
        _onDragLeave() {
            this.droptargetCounter--;
        },
        _onDragEnd() {
            this.droptargetCounter = 0;
        },
        _onDragOver() {
            event.preventDefault();
            event.stopPropagation();
        },
        _onDrop(event) {
            event.preventDefault();
            event.stopPropagation();
            if(this.droptargetCanHandle) {
                try {
                    this.onDrop(event);
                } catch (error) {
                    console.console.warn(error);
                }
            }
            this.droptargetCounter = 0;
        },
    }
}

export { Droptarget }