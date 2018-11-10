let argv         = require('minimist')(process.argv.slice(2));
let autoprefixer = require('gulp-autoprefixer');
let cache        = require('gulp-cached');
let chmod        = require('gulp-chmod');
let concat       = require('gulp-concat');
let git          = require('gulp-git');
let gulpif       = require('gulp-if');
let gulp         = require('gulp');
let livereload   = require('gulp-livereload');
let plumber      = require('gulp-plumber');
let pug          = require('gulp-pug');
let rename       = require('gulp-rename');
let sass         = require('gulp-sass');
let sourcemaps   = require('gulp-sourcemaps');
let uglify       = require('gulp-uglify-es').default;

let enabled = {
    uglify: argv.production,
    maps: !argv.production,
    failCheck: !argv.production,
    prettyPug: !argv.production,
    cachify: !argv.production,
    cleanup: argv.production,
    chmod: argv.production,
};

let destination = {
    css: 'pillar/web/static/assets/css',
    pug: 'pillar/web/templates',
    js: 'pillar/web/static/assets/js',
}

let source = {
    bootstrap: 'node_modules/bootstrap/',
    jquery: 'node_modules/jquery/',
    popper: 'node_modules/popper.js/'
}

/* Stylesheets */
gulp.task('styles', function(done) {
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
    done();
});


/* Templates */
gulp.task('templates', function(done) {
    gulp.src('src/templates/**/*.pug')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.cachify, cache('templating')))
        .pipe(pug({
            pretty: enabled.prettyPug
        }))
        .pipe(gulp.dest(destination.pug))
        .pipe(gulpif(argv.livereload, livereload()));
    done();
});


/* Individual Uglified Scripts */
gulp.task('scripts', function(done) {
    gulp.src('src/scripts/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.cachify, cache('scripting')))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(rename({suffix: '.min'}))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulpif(enabled.chmod, chmod(0o644)))
        .pipe(gulp.dest(destination.js))
        .pipe(gulpif(argv.livereload, livereload()));
    done();
});


/* Collection of scripts in src/scripts/tutti/ to merge into tutti.min.js
 * Since it's always loaded, it's only for functions that we want site-wide.
 * It also includes jQuery and Bootstrap (and its dependency popper), since
 * the site doesn't work without it anyway.*/
gulp.task('scripts_concat_tutti', function(done) {

    toUglify = [
        source.jquery    + 'dist/jquery.min.js',
        source.popper    + 'dist/umd/popper.min.js',
        source.bootstrap + 'js/dist/index.js',
        source.bootstrap + 'js/dist/util.js',
        source.bootstrap + 'js/dist/alert.js',
        source.bootstrap + 'js/dist/collapse.js',
        source.bootstrap + 'js/dist/dropdown.js',
        source.bootstrap + 'js/dist/tooltip.js',
        'src/scripts/tutti/**/*.js'
    ];

    gulp.src(toUglify)
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(concat("tutti.min.js"))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulpif(enabled.chmod, chmod(0o644)))
        .pipe(gulp.dest(destination.js))
        .pipe(gulpif(argv.livereload, livereload()));
    done();
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
gulp.task('watch',function(done) {
    // Only listen for live reloads if ran with --livereload
    if (argv.livereload){
        livereload.listen();
    }

    gulp.watch('src/styles/**/*.sass',gulp.series('styles'));
    gulp.watch('src/templates/**/*.pug',gulp.series('templates'));
    gulp.watch('src/scripts/*.js',gulp.series('scripts'));
    gulp.watch('src/scripts/tutti/**/*.js',gulp.series('scripts_concat_tutti'));

    done();
});


// Erases all generated files in output directories.
gulp.task('cleanup', function(done) {
    let paths = [];
    for (attr in destination) {
        paths.push(destination[attr]);
    }

    git.clean({ args: '-f -X ' + paths.join(' ') }, function (err) {
        if(err) throw err;
    });
    done();
});


// Run 'gulp' to build everything at once
let tasks = [];
if (enabled.cleanup) tasks.push('cleanup');
// gulp.task('default', gulp.parallel('styles', 'templates', 'scripts', 'scripts_tutti'));

gulp.task('default', gulp.parallel(tasks.concat([
    'styles',
    'templates',
    'scripts',
    'scripts_concat_tutti',
    'scripts_move_vendor',
])));
