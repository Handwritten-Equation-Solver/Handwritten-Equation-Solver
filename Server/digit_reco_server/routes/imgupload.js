var express = require('express');
var router = express.Router();
var path = require('path');
var multer = require('multer');
var uploader = multer({dest : './Images'});
var fs = require('fs');

var predictor = require('../predictor/use_keras_model');
var spawn = require("child_process").spawn;

var MY_ANACONDA_ENV = 'G:\\Ananconda\\envs\\tensorflow\\python.exe'

/* GET home page. */
router.post('/', uploader.single('digitimage'), function(req, res, next) {
    var temp_path = req.file.path;
    var target_path = './Images/' + req.file.originalname;

    fs.rename(temp_path, target_path, function(err){
        var segmentProcess = spawn(MY_ANACONDA_ENV, [path.resolve("./python_utils/segment.py"), path.resolve(target_path)]);
        segmentProcess.stdout.on('data', function(data){
            console.log(data.toString());

            res.setHeader('Content-Type', 'application/json');
            res.send(JSON.stringify({solution: data.toString()}));
        });
        segmentProcess.stderr.on('data', function(data){
            console.log(data.toString());
            //res.send('Error Occured');
        });
    });
});

module.exports = router;