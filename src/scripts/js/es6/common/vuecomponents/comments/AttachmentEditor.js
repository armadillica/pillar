import { thenGetFileDocument, getFileVariation } from '../../api/files'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'

const VALID_NAME_REGEXP = /[a-zA-Z0-9_\-]+/g;
const NON_VALID_NAME_REGEXP = /[^a-zA-Z0-9_\-]+/g;
const TEMPLATE = `
<div class="attachment"
    :class="{error: !isSlugOk}"
>
    <div class="thumbnail-container"
        @click="$emit('insert', oid)"
        title="Click to add to comment"
    >
        <i :class="thumbnailBackup"
            v-show="!thumbnail"
        />
        <img class="preview-thumbnail"
            v-if="!!thumbnail"
            :src="thumbnail"
            width=50
            height=50
        />
    </div>
    <input class="form-control"
        title="Slug"
        v-model="newSlug"
    />
    <div class="actions">
        <div class="action delete"
            @click="$emit('delete', oid)"
        >
            <i class="pi-trash"/>
            Delete
        </div>
    </div>
</div>
`;

Vue.component('comment-attachment-editor', {
    template: TEMPLATE,
    mixins: [UnitOfWorkTracker],
    props: {
        slug: String,
        allSlugs: Array,
        oid: String
    },
    data() {
        return {
            newSlug: this.slug,
            thumbnail: '',
            thumbnailBackup: 'pi-spin spin',
        }
    },
    computed: {
        isValidAttachmentName() {
            let regexpMatch = this.slug.match(VALID_NAME_REGEXP);
            return !!regexpMatch && regexpMatch.length === 1 && regexpMatch[0] === this.slug;
        },
        isUnique() {
            let countOccurrences = 0;
            for (let s of this.allSlugs) {
                // Don't worry about unicode. isValidAttachmentName denies those anyway
                if (s.toUpperCase() === this.slug.toUpperCase()) {
                    countOccurrences++;
                }
            }
            return countOccurrences === 1;
        },
        isSlugOk() {
            return this.isValidAttachmentName && this.isUnique;
        }
    },
    watch: {
        newSlug(newValue, oldValue) {
            this.$emit('rename', newValue, this.oid);
        },
        isSlugOk(newValue, oldValue) {
            this.$emit('validation', this.oid, newValue);
        }
    },
    created() {
        this.newSlug = this.makeSafeAttachmentString(this.slug);
        this.$emit('validation', this.oid, this.isSlugOk);

        this.unitOfWork(
            thenGetFileDocument(this.oid)
            .then((fileDoc) => {
                let content_type = fileDoc.content_type
                if (content_type.startsWith('image')) {
                    try {
                        let imgFile = getFileVariation(fileDoc, 's');
                        this.thumbnail = imgFile.link;
                    } catch (error) {
                        this.thumbnailBackup = 'pi-image';
                    }
                } else if(content_type.startsWith('video')) {
                    this.thumbnailBackup = 'pi-video';
                } else {
                    this.thumbnailBackup = 'pi-file';
                }
            })
        );
    },
    methods: {
        /**
         * Replaces all spaces with underscore and removes all o
         * @param {String} unsafe 
         * @returns {String} 
         */
        makeSafeAttachmentString(unsafe) {
            let candidate = (unsafe);
            let matchSpace = / /g;
            candidate = candidate
                .replace(matchSpace, '_')
                .replace(NON_VALID_NAME_REGEXP, '')
            
            return candidate || `${this.oid}`
        }
    }
});