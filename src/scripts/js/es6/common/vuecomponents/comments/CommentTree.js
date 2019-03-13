import './CommentEditor'
import './Comment'
import './CommentsLocked'
import '../user/Avatar'
import '../utils/GenericPlaceHolder'
import { thenGetComments } from '../../api/comments'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'
import { EventBus, Events } from './EventBus'

const TEMPLATE = `
<section class="comments-tree">
    <div class="comment-reply-container"
        v-if="canReply"
    >
        <user-avatar
            :user="user"
        />
        <comment-editor
            v-if="canReply"
            mode="reply"
            @unit-of-work="childUnitOfWork"
            :projectId="projectId"
            :parentId="parentId"
            :user="user"
        />
    </div>
    <comments-locked
        v-if="readOnly||!isLoggedIn"
        :user="user"
    />
    <div class="comments-list-title">{{ numberOfCommentsStr }}</div>
    <div class="comments-list">
        <comment
            v-for="c in comments"
            @unit-of-work="childUnitOfWork"
            :readOnly=readOnly||!isLoggedIn
            :comment="c"
            :user="user"
            :key="c.id"/>
    </div>
    <generic-placeholder
        v-show="showLoadingPlaceholder"
        label="Loading Comments..."
    />
</section>
`;

Vue.component('comments-tree', {
    template: TEMPLATE,
    mixins: [UnitOfWorkTracker],
    props: {
        parentId: String,
        readOnly: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            replyHidden: false,
            nbrOfComments: 0,
            projectId: '',
            comments: [],
            showLoadingPlaceholder: true,
            user: pillar.utils.getCurrentUser(),
            canPostComments: this.canPostCommentsStr == 'true'
        }
    },
    computed: {
        numberOfCommentsStr() {
            let pluralized = this.nbrOfComments === 1 ? 'Comment' : 'Comments'
            return `${ this.nbrOfComments } ${ pluralized }`;
        },
        isLoggedIn() {
            return this.user.is_authenticated;
        },
        iSubscriber() {
            return this.user.hasCap('subscriber');
        },
        canRenewSubscription() {
            return this.user.hasCap('can-renew-subscription');
        },
        canReply() {
            return !this.readOnly && !this.replyHidden && this.isLoggedIn;
        }
    },
    watch: {
        isBusyWorking(isBusy) {
            if(isBusy) {
                $(document).trigger('pillar:workStart');
            } else {
                $(document).trigger('pillar:workStop');
            }
        },
        parentId() {
            this.fetchComments();
        }
    },
    created() {
        EventBus.$on(Events.BEFORE_SHOW_EDITOR, this.doHideEditors);
        EventBus.$on(Events.EDIT_DONE, this.showReplyComponent);
        EventBus.$on(Events.NEW_COMMENT, this.onNewComment);
        EventBus.$on(Events.UPDATED_COMMENT, this.onCommentUpdated);
        this.fetchComments()
    },
    beforeDestroy() {
        EventBus.$off(Events.BEFORE_SHOW_EDITOR, this.doHideEditors);
        EventBus.$off(Events.EDIT_DONE, this.showReplyComponent);
        EventBus.$off(Events.NEW_COMMENT, this.onNewComment);
        EventBus.$off(Events.UPDATED_COMMENT, this.onCommentUpdated);
        if(this.isBusyWorking) {
            $(document).trigger('pillar:workStop');
        }
    },
    methods: {
        fetchComments() {
            this.showLoadingPlaceholder = true;
            this.unitOfWork(
                thenGetComments(this.parentId)
                .then((commentsTree) => {
                    this.nbrOfComments = commentsTree['nbr_of_comments'];
                    this.comments = commentsTree['comments'];
                    this.projectId = commentsTree['project'];
                })
                .fail((err) => {toastr.error(pillar.utils.messageFromError(err), 'Failed to load comments')})
                .always(()=>this.showLoadingPlaceholder = false)
            );
        },
        doHideEditors() {
            this.replyHidden = true;
        },
        showReplyComponent() {
            this.replyHidden = false;
        },
        onNewComment(newComment) {
            this.nbrOfComments++;
            let parentArray;
            if(newComment.parent === this.parentId) {
                parentArray = this.comments;
            } else {
                let parentComment = this.findComment(this.comments, (comment) => {
                    return comment.id === newComment.parent;
                });
                parentArray = parentComment.replies;
            }
            parentArray.unshift(newComment);
            this.$emit('new-comment');
        },
        onCommentUpdated(updatedComment) {
            let commentInTree = this.findComment(this.comments, (comment) => {
                return comment.id === updatedComment.id;
            });
            delete updatedComment.replies; // No need to apply these since they should be the same
            Object.assign(commentInTree, updatedComment);
        },
        findComment(arrayOfComments, matcherCB) {
            for(let comment of arrayOfComments) {
                if(matcherCB(comment)) {
                    return comment;
                }
                let match = this.findComment(comment.replies, matcherCB);
                if (match) {
                    return match;
                }
            }
        }
    },
});
