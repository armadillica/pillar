import '../utils/MarkdownPreview'
import './AttachmentEditor'
import './UploadProgress'
import { thenCreateComment, thenUpdateComment } from '../../api/comments'
import { thenUploadFile } from '../../api/files'
import { Droptarget } from '../mixins/Droptarget'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'
import { EventBus, Events } from './EventBus'

const MAX_ATTACHMENTS = 5;

const TEMPLATE =`
<div class="comment-reply-form"
    :class="dropTargetClasses"
>
    <div class="attachments">
        <comment-attachment-editor
            v-for="a in attachments"
            @delete="attachmentDelete"
            @insert="insertAttachment"
            @rename="attachmentRename"
            @validation="attachmentValidation"
            @unit-of-work="childUnitOfWork"
            :slug="a.slug"
            :allSlugs="allSlugs"
            :oid="a.oid"
            :key="a.oid"
        />
        <upload-progress
            v-if="uploads.nbrOfActive > 0"
            :label="uploadProgressLabel"
            :progress="uploadProgressPercent"
        />
    </div>
    <div class="comment-reply-field"
        :class="{filled: isMsgLongEnough}"
    >
        <textarea
            ref="inputField"
            @keyup="keyUp"
            v-model="msg"
            id="comment_field"
            placeholder="Join the conversation...">
        </textarea>
        <div class="comment-reply-meta">
            <button class="comment-action-submit"
                :class="{disabled: !canSubmit}"
                @click="submit"
                type="button"
                title="Post Comment (Ctrl+Enter)">
                <span>
                    <i :class="submitButtonIcon"/>{{ submitButtonText }}
                </span>
                <span class="hotkey">Ctrl + Enter</span>
            </button>
        </div>
    </div>
    <markdown-preview
        v-show="msg.length > 0"
        :markdown="msg"
        :attachments="attachmentsAsObject"
    />
</div>
`;

Vue.component('comment-editor', {
    template: TEMPLATE,
    mixins: [Droptarget, UnitOfWorkTracker],
    props: {
        user: Object,
        parentId: String,
        projectId: String,
        comment: Object,
        mode: {
            type: String,
            default: 'reply', // reply or update
        },
    },
    data() {
        return {
            msg: this.initialMsg(),
            attachments: this.initialAttachments(),
            uploads: {
                nbrOfActive: 0,
                nbrOfTotal: 0,
                total: 0,
                loaded: 0
            },
        }
    },
    computed: {
        submitButtonText() {
            switch(this.mode) {
                case 'reply': return 'Send';
                case 'update': return 'Update';
                default: console.error('Unknown mode: ', this.mode);
            }
        },
        submitButtonIcon() {
            if (this.isBusyWorking) {
                return 'pi-spin spin';
            }else{
                switch(this.mode) {
                    case 'reply': return 'pi-paper-plane';
                    case 'update': return 'pi-check';
                    default: console.error('Unknown mode: ', this.mode);
                }
            }
        },
        attachmentsAsObject() {
            let attachmentsObject = {};
            for (let a of this.attachments) {
                attachmentsObject[a.slug] = {oid: a.oid};
            }
            return attachmentsObject;
        },
        allSlugs() {
            return this.attachments.map((a) => {
                return a['slug'];
            });
        },
        isMsgLongEnough() {
            return this.msg.length >= 5;
        },
        isAttachmentsValid() {
            for (let att of this.attachments) {
                if(!att.isSlugValid) {
                    return false;
                }
            }
            return true;
        },
        isValid() {
            return this.isAttachmentsValid && this.isMsgLongEnough;
        },
        canSubmit() {
            return this.isValid && !this.isBusyWorking;
        },
        uploadProgressPercent() {
            if (this.uploads.nbrOfActive === 0 || this.uploads.total === 0) {
                return 100;
            }
            return this.uploads.loaded / this.uploads.total * 100;
        },
        uploadProgressLabel() {
            if (this.uploadProgressPercent === 100) {
                return 'Processing'
            }
            if (this.uploads.nbrOfTotal === 1) {
                return 'Uploading file';
            } else {
                let fileOf = this.uploads.nbrOfTotal - this.uploads.nbrOfActive + 1;
                return `Uploading ${fileOf}/${this.uploads.nbrOfTotal} files`;
            }
        },
    },
    watch:{
        msg(){
            this.autoSizeInputField();
        }
    },
    mounted() {
        if(this.comment) {
            this.$nextTick(function () {
                this.autoSizeInputField();
                this.$refs.inputField.focus();
            })
        }
    },
    methods: {
        initialMsg() {
            if (this.comment) {
                if (this.mode === 'reply') {
                    return `***@${this.comment.user.full_name}*** `;
                }
                if (this.mode === 'update') {
                    return this.comment.msg_markdown;
                }
            }
            return '';
        },
        initialAttachments() {
            // Transforming the attacmentobject to an array of attachments
            let attachmentsList = []
            if(this.mode === 'update') {
                let attachmentsObj = this.comment.properties.attachments
                for (let k in attachmentsObj) {
                    if (attachmentsObj.hasOwnProperty(k)) {
                        let a = {
                            slug: k,
                            oid: attachmentsObj[k]['oid'],
                            isSlugValid: true
                        }
                        attachmentsList.push(a);
                     }
                }
            }
            return attachmentsList;
        },
        submit() {
            if(!this.canSubmit) return;
            this.unitOfWork(
                this.thenSubmit()
                .fail((err) => {toastr.error(pillar.utils.messageFromError(err), 'Failed to submit comment')})
            );
        },
        thenSubmit() {
            if (this.mode === 'reply') {
                return this.thenCreateComment();
            } else {
                return this.thenUpdateComment();
            }
        },
        keyUp(e) {
            if ((e.keyCode == 13 || e.key === 'Enter') && e.ctrlKey) {
				this.submit();
			}
        },
        thenCreateComment() {
            return thenCreateComment(this.parentId, this.msg, this.attachmentsAsObject)
            .then((newComment) => {
                EventBus.$emit(Events.NEW_COMMENT, newComment);
                EventBus.$emit(Events.EDIT_DONE, newComment.id );
                this.cleanUp();
            })
        },
        thenUpdateComment() {
            return thenUpdateComment(this.comment.parent, this.comment.id, this.msg, this.attachmentsAsObject)
            .then((updatedComment) => {
                EventBus.$emit(Events.UPDATED_COMMENT, updatedComment);
                EventBus.$emit(Events.EDIT_DONE, updatedComment.id);
                this.cleanUp();
            })
        },
        canHandleDrop(event) {
            let dataTransfer = event.dataTransfer;
            let items = [...dataTransfer.items];
            let nbrOfAttachments = items.length + this.uploads.nbrOfActive + this.attachments.length;
            if(nbrOfAttachments > MAX_ATTACHMENTS) {
                // Exceeds the limit
                return false;
            }
            // Only files in drop
            return [...dataTransfer.items].reduce((prev, it) => {
                let isFile = it.kind === 'file' && !!it.type;
                return prev && isFile;
            }, !!items.length);
        },
        onDrop(event) {
            let files =  [...event.dataTransfer.files];
            for (let f of files) {
                this.unitOfWork(
                    this.thenUploadFile(f)
                    .fail((err) => {toastr.error(pillar.utils.messageFromError(err), 'File upload failed')})
                );
            }
        },
        thenUploadFile(file){
            let lastReportedTotal = 0;
            let lastReportedLoaded = 0;
            let progressCB = (total, loaded) => {
                this.uploads.loaded += loaded - lastReportedLoaded;
                this.uploads.total += total - lastReportedTotal;
                lastReportedLoaded = loaded;
                lastReportedTotal = total;
            }
            this.uploads.nbrOfActive++;
            this.uploads.nbrOfTotal++;
            return thenUploadFile(this.projectId || this.comment.project, file, progressCB)
                .then((resp) => {
                    let attachment = {
                        slug: file.name,
                        oid: resp['file_id'],
                        isSlugValid: false
                    }
                    this.attachments.push(attachment);
                    this.msg += this.getAttachmentMarkdown(attachment);
                })
                .always(()=>{
                    this.uploads.nbrOfActive--;
                    if(this.uploads.nbrOfActive === 0) {
                        this.uploads.loaded = 0;
                        this.uploads.total = 0;
                        this.uploads.nbrOfTotal = 0;
                    }
                })
        },
        getAttachmentMarkdown(attachment){
            return `{attachment ${attachment.slug}}`;
        },
        insertAttachment(oid){
            let attachment = this.getAttachment(oid);
            this.msg += this.getAttachmentMarkdown(attachment);
        },
        attachmentDelete(oid) {
            let attachment = this.getAttachment(oid);
            let markdownToRemove = this.getAttachmentMarkdown(attachment);
            this.msg = this.msg.replace(new RegExp(markdownToRemove,'g'), '');
            this.attachments = this.attachments.filter((a) => {return a.oid !== oid});
        },
        attachmentRename(newName, oid) {
            let attachment = this.getAttachment(oid);
            let oldMarkdownAttachment = this.getAttachmentMarkdown(attachment);
            attachment.slug = newName;
            let newMarkdownAttachment = this.getAttachmentMarkdown(attachment);

            this.msg = this.msg.replace(new RegExp(oldMarkdownAttachment,'g'), newMarkdownAttachment);
        },
        getAttachment(oid) {
            for (let a of this.attachments) {
                if (a.oid === oid) return a;
            }
            console.error('No attachment found:', oid);
        },
        attachmentValidation(oid, isValid) {
            let attachment = this.getAttachment(oid);
            attachment.isSlugValid = isValid;
        },
        cleanUp() {
            this.msg = '';
            this.attachments = [];
        },
        autoSizeInputField() {
            let elInputField = this.$refs.inputField;
            elInputField.style.cssText = 'height:auto; padding:0';
            let newInputHeight = elInputField.scrollHeight + 20;
            elInputField.style.cssText = `height:${ newInputHeight }px`;
        }
    }
});