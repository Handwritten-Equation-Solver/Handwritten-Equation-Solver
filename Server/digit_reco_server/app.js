var express = require('express');
var path = require('path');
var favicon = require('serve-favicon');
var logger = require('morgan');
var cookieParser = require('cookie-parser');
var bodyParser = require('body-parser');

var index_route = require('./routes/index');
var users_route = require('./routes/users');
var imgupload_route = require('./routes/imgupload');
var graphplot_route = require('./routes/graphplot');
var seqsolve_route = require('./routes/seqsolve');
var simultsolve_route = require('./routes/simultsolve');
var eqnsolve_route = require('./routes/eqnsolve');

var app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

// uncomment after placing your favicon in /public
//app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

app.use('/', index_route);
app.use('/users', users_route);
app.use('/imgupload', imgupload_route);
app.use('/graphplot', graphplot_route);
app.use('/seqsolve', seqsolve_route);
app.use('/simultsolve', simultsolve_route);
app.use('/eqnsolve', eqnsolve_route);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  var err = new Error('Not Found');
  err.status = 404;
  next(err);
});

// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

module.exports = app;
