import '../user/Avatar'
import '../utils/PrettyCreated'
import './CommentEditor'
import './Rating'
import { Linkable } from '../mixins/Linkable'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'
import { EventBus, Events } from './EventBus'

const TEMPLATE = `
<div class="comment-branch">
    <div class="comment-container"
        :class="{'is-first': !isReply, 'is-reply': isReply, 'comment-linked': isLinked}"
        :id="comment.id">
        <div class="comment-avatar">
            <user-avatar
                :user="comment.user"
            />
            <div class="user-badges"
                v-html="comment.user.badges_html">
            </div>
        </div>
        <div class="comment-content">
            <div class="comment-body"
                v-if="!isUpdating"
            >
                <p class="comment-author">
                    {{ comment.user.full_name }}
                </p>
                <span class="comment-msg">
                    <p v-html="comment.msg_html"/>
                </span>
            </div>
            <comment-editor
                v-if="isUpdating"
                @unit-of-work="childUnitOfWork"
                :mode="editorMode"
                :comment="comment"
                :user="user"
                :parentId="comment.id"
            />
            <div class="comment-meta">
                <comment-rating
                    :comment="comment"
                    @unit-of-work="childUnitOfWork"
                />
                <div class="comment-action">
                    <span class="action" title="Reply to this comment"
                        v-if="canReply"
                        @click="showReplyEditor"
                    >
                        Reply
                    </span>
                    <span class="action" title="Edit comment"
                        v-if="canUpdate"
                        @click="showUpdateEditor"
                    >
                        Edit
                    </span>
                    <span class="action" title="Cancel changes"
                        v-if="canCancel"
                        @click="cancleEdit"
                    >
                        <i class="pi-cancel"></i>Cancel
                    </span>
                </div>
                <pretty-created
                    :created="comment.created"
                    :updated="comment.updated"
                />
            </div>
        </div>
    </div>
    <div class="comment-reply-container is-reply"
        v-if="isReplying"
    >
        <user-avatar
            :user="user"
        />
        <comment-editor
            v-if="isReplying"
            @unit-of-work="childUnitOfWork"
            :mode="editorMode"
            :comment="comment"
            :user="user"
            :parentId="comment.id"
        />
    </div>
    <div class="comments-list">
        <comment
            v-for="c in comment.replies"
            @unit-of-work="childUnitOfWork"
            isReply=true
            :readOnly="readOnly"
            :comment="c"
            :user="user"
            :key="c.id"/>
    </div>
</div>
`;

Vue.component('comment', {
    template: TEMPLATE,
    mixins: [Linkable, UnitOfWorkTracker],
    props: {
        user: Object,
        comment: Object,
        readOnly: {
            type: Boolean,
            default: false,
        },
        isReply: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            isReplying: false,
            isUpdating: false,
            id: this.comment.id,
        }
    },
    computed: {
        canUpdate() {
            return !this.readOnly && this.comment.user.id === this.user.user_id && !this.isUpdating && !this.isReplying;
        },
        canReply() {
            return !this.readOnly && !this.isUpdating && !this.isReplying;
        },
        canCancel() {
            return this.isReplying || this.isUpdating;
        },
        editorMode() {
            if(this.isReplying) {
                return 'reply';
            }
            if(this.isUpdating) {
                return 'update';
            }
        }
    },
    created() {
        EventBus.$on(Events.BEFORE_SHOW_EDITOR, this.doHideEditors);
        EventBus.$on(Events.EDIT_DONE, this.doHideEditors);
    },
    beforeDestroy() {
        EventBus.$off(Events.BEFORE_SHOW_EDITOR, this.doHideEditors);
        EventBus.$off(Events.EDIT_DONE, this.doHideEditors);
    },
    methods: {
        showReplyEditor() {
            EventBus.$emit(Events.BEFORE_SHOW_EDITOR, this.comment.id );
            this.isReplying = true;
        },
        showUpdateEditor() {
            EventBus.$emit(Events.BEFORE_SHOW_EDITOR, this.comment.id );
            this.isUpdating = true;
        },
        cancleEdit() {
            this.doHideEditors();
            EventBus.$emit(Events.EDIT_DONE);
        },
        doHideEditors() {
            this.isReplying = false;
            this.isUpdating = false;
        },
    }
});
