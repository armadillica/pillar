import { debounced } from '../../utils/init'
import { thenMarkdownToHtml } from '../../api/markdown'
import { UnitOfWorkTracker } from '../mixins/UnitOfWorkTracker'
const TEMPLATE = `
<div class="markdown-preview">
    <div class="markdown-preview-md"
        v-html="asHtml"/>
    <div class="markdown-preview-info">
        <a
            title="Handy guide of Markdown syntax"
            target="_blank"
            href="http://commonmark.org/help/">
            <span>markdown cheatsheet</span>
        </a>
    </div>
</div>
`;

Vue.component('markdown-preview', {
    template: TEMPLATE,
    mixins: [UnitOfWorkTracker],
    props: {
        markdown: String,
        attachments: Object
    },
    data() {
        return {
            asHtml: '',
        }
    },
    created() {
        this.markdownToHtml(this.markdown, this.attachments);
        this.debouncedMarkdownToHtml = debounced(this.markdownToHtml);
    },
    watch: {
        markdown(newValue, oldValue) {
            this.debouncedMarkdownToHtml(newValue, this.attachments);
        },
        attachments(newValue, oldValue) {
            this.debouncedMarkdownToHtml(this.markdown, newValue);
        }
    },
    methods: {
        markdownToHtml(markdown, attachments) {
            this.unitOfWork(
                thenMarkdownToHtml(markdown, attachments)
                .then((data) => {
                    this.asHtml = data.content;
                })
                .fail((err) => {
                    toastr.error(xhrErrorResponseMessage(err), 'Parsing failed');
                })
            );
        }
    }
});