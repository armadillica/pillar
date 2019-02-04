import { EventBus, Events } from './EventBus'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'
import { thenVoteComment } from '../../api/comments'
const TEMPLATE = `
<div class="comment-rating"
    :class="{rated: currentUserHasRated, positive: currentUserRatedPositive }"
    >
    <div class="comment-rating-value" title="Number of likes">{{ rating }}</div>
    <div class="comment-action-rating up" title="Like comment"
        v-if="canVote"
        @click="upVote"
    />
</div>
`;

Vue.component('comment-rating', {
    template: TEMPLATE,
    mixins: [UnitOfWorkTracker],
    props: {comment: Object},
    computed: {
        positiveRating() {
            return this.comment.properties.rating_positive || 0;
        },
        negativeRating() {
            return this.comment.properties.rating_negative || 0;
        },
        rating() {
            return this.positiveRating - this.negativeRating;
        },
        currentUserRatedPositive() {
            return this.comment.current_user_rating === true;
        },
        currentUserHasRated() {
            return typeof this.comment.current_user_rating === "boolean" ;
        },
        canVote() {
            return this.comment.user.id !== pillar.utils.getCurrentUser().user_id;
        }
    },
    methods: {
        upVote() {
            let vote = this.comment.current_user_rating === true ? 0 : 1; // revoke if set
            this.unitOfWork(
                thenVoteComment(this.comment.parent, this.comment.id, vote)
                .then((updatedComment) => {
                    EventBus.$emit(Events.UPDATED_COMMENT, updatedComment);
                })
                .fail((err) => {toastr.error(pillar.utils.messageFromError(err), 'Faied to vote on comment')})
            );
        }
    }
});
