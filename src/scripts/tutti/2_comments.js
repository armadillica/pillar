
/* Reply */
$(document).on('click','body .comment-action-reply',function(e){
	e.preventDefault();

	// container of the comment we are replying to
	var parentDiv = $(this).parent().parent();

	// container of the first-level comment in the thread
	var parentDivFirst = $(this).parent().parent().prevAll('.is-first:first');

	// Get the id of the comment
	if (parentDiv.hasClass('is-reply')) {
		parentNodeId = parentDivFirst.data('node_id');
	} else {
		parentNodeId = parentDiv.data('node_id');
	}

	// Get the textarea and set its parent_id data
	var commentField = document.getElementById('comment_field');
	commentField.setAttribute('data-parent_id', parentNodeId);

	// Start the comment field with @authorname:
	var replyAuthor = $(this).parent().parent().find('.comment-author:first span').html();
	$(commentField).val("**@" + replyAuthor.slice(1, -1) + ":** ");

	// Add class for styling
	$('.comment-container').removeClass('is-replying');
	parentDiv.addClass('is-replying');

	// Rename Post Comment button to Reply
	var commentSubmitButton = document.getElementById('comment_submit');
	$(commentSubmitButton).text('Post Reply');

	// Move comment-reply container field after the parent container
	var commentForm = $('.comment-reply-container').detach();
	parentDiv.after(commentForm);
	// document.getElementById('comment_field').focus();
	$(commentField).focus();

	// Convert Markdown
	var convert = new Markdown.getSanitizingConverter().makeHtml;
	var preview = $('.comment-reply-preview');
	preview.html(convert($(commentField).val()));
	$('.comment-reply-form').addClass('filled');
});


/* Cancel Reply */
$(document).on('click','body .comment-action-cancel',function(e){
	e.preventDefault();

	$('.comment-reply-container').detach().prependTo('#comments-list');
	var commentField = document.getElementById('comment_field');
	$(commentField).val('');
	// Convert Markdown
	var convert = new Markdown.getSanitizingConverter().makeHtml;
	var preview = $('.comment-reply-preview');
	preview.html(convert($(commentField).val()));

	var commentSubmitButton = document.getElementById('comment_submit');
	$(commentSubmitButton).text('Post Comment');

	$('.comment-reply-form').removeClass('filled');
	$('.comment-container').removeClass('is-replying');
});


/* Rate */
$(document).on('click','body .comment-action-rating',function(e){
	e.preventDefault();

	var $this = $(this);
	var nodeId = $this.parent().parent().parent().data('node_id');
	var is_positive = !$this.hasClass('down');
	var parentDiv = $this.parent();
	var rated_positive = parentDiv.hasClass('positive');

	var op;
	if (parentDiv.hasClass('rated') && is_positive == rated_positive) {
		op = 'revoke';
	} else if (is_positive) {
		op = 'upvote';
	} else {
		op = 'downvote';
	}

	$.post("/nodes/comments/" + nodeId + "/rate/" + op)
	.done(function(data){

		// Add/remove styles for rated statuses
		switch(op) {
			case 'revoke':
				parentDiv.removeClass('rated');
				break;
			case 'upvote':
				parentDiv.addClass('rated');
				parentDiv.addClass('positive');
				break;
			case 'downvote':
				parentDiv.addClass('rated');
				parentDiv.removeClass('positive');
				break;
		}

		var rating = data['data']['rating_positive'] - data['data']['rating_negative'];
		$this.siblings('.comment-rating-value').text(rating);
	});
});
