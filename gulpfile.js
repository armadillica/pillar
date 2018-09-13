var argv         = require('minimist')(process.argv.slice(2));
var autoprefixer = require('gulp-autoprefixer');
var cache        = require('gulp-cached');
var chmod        = require('gulp-chmod');
var concat       = require('gulp-concat');
var git          = require('gulp-git');
var gulpif       = require('gulp-if');
var gulp         = require('gulp');
var livereload   = require('gulp-livereload');
var plumber      = require('gulp-plumber');
var pug          = require('gulp-pug');
var rename       = require('gulp-rename');
var sass         = require('gulp-sass');
var sourcemaps   = require('gulp-sourcemaps');
var uglify       = require('gulp-uglify-es').default;

var enabled = {
    uglify: argv.production,
    maps: !argv.production,
    failCheck: !argv.production,
    prettyPug: !argv.production,
    cachify: !argv.production,
    cleanup: argv.production,
    chmod: argv.production,
};

var destination = {
    css: 'pillar/web/static/assets/css',
    pug: 'pillar/web/templates',
    js: 'pillar/web/static/assets/js',
}

var source = {
    bootstrap: 'node_modules/bootstrap/',
    jquery: 'node_modules/jquery/',
    popper: 'node_modules/popper.js/'
}

/* CSS */
gulp.task('styles', function() {
    gulp.src('src/styles/**/*.sass')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(sass({
            outputStyle: 'compressed'}
            ))
        .pipe(autoprefixer("last 3 versions"))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulp.dest(destination.css))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Templates - Pug */
gulp.task('templates', function() {
    gulp.src('src/templates/**/*.pug')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.cachify, cache('templating')))
        .pipe(pug({
            pretty: enabled.prettyPug
        }))
        .pipe(gulp.dest(destination.pug))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Individual Uglified Scripts */
gulp.task('scripts', function() {
    gulp.src('src/scripts/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.cachify, cache('scripting')))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(rename({suffix: '.min'}))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulpif(enabled.chmod, chmod(644)))
        .pipe(gulp.dest(destination.js))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Collection of scripts in src/scripts/tutti/ to merge into tutti.min.js
 * Since it's always loaded, it's only for functions that we want site-wide.
 * It also includes jQuery and Bootstrap (and its dependency popper), since
 * the site doesn't work without it anyway.*/
gulp.task('scripts_concat_tutti', function() {

    toUglify = [
        source.jquery    + 'dist/jquery.min.js',
        source.popper    + 'dist/umd/popper.min.js',
        source.bootstrap + 'js/dist/index.js',
        source.bootstrap + 'js/dist/util.js',
        source.bootstrap + 'js/dist/tooltip.js',
        source.bootstrap + 'js/dist/dropdown.js',
        'src/scripts/tutti/**/*.js'
    ];

    gulp.src(toUglify)
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(concat("tutti.min.js"))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulpif(enabled.chmod, chmod(644)))
        .pipe(gulp.dest(destination.js))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Simply move these vendor scripts from node_modules. */
gulp.task('scripts_move_vendor', function(done) {

    let toMove = [
    'node_modules/video.js/dist/video.min.js',
    ];

    gulp.src(toMove)
    .pipe(gulp.dest(destination.js + '/vendor/'));
    done();
});


// While developing, run 'gulp watch'
gulp.task('watch',function() {
    // Only listen for live reloads if ran with --livereload
    if (argv.livereload){
        livereload.listen();
    }

    gulp.watch('src/styles/**/*.sass',['styles']);
    gulp.watch('src/templates/**/*.pug',['templates']);
    gulp.watch('src/scripts/*.js',['scripts']);
    gulp.watch('src/scripts/tutti/**/*.js',['scripts_concat_tutti']);
});


// Erases all generated files in output directories.
gulp.task('cleanup', function() {
    var paths = [];
    for (attr in destination) {
        paths.push(destination[attr]);
    }

    git.clean({ args: '-f -X ' + paths.join(' ') }, function (err) {
        if(err) throw err;
    });

});


// Run 'gulp' to build everything at once
var tasks = [];
if (enabled.cleanup) tasks.push('cleanup');
gulp.task('default', tasks.concat([
    'styles',
    'templates',
    'scripts',
    'scripts_concat_tutti',
    'scripts_move_vendor',
]));
