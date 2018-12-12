const TEMPLATE = `
<div class="upload-progress">
    <label>
        {{ label }}
    </label>
    <progress class="progress-uploading"
        max="100" 
        :value="progress"
    >
    </progress>
</div>
`;

Vue.component('upload-progress', {
    template: TEMPLATE,
    props: {
        label: String,
        progress: {
            type: Number,
            default: 0
        }
    },
});