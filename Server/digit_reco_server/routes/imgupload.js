var express = require('express');
var router = express.Router();
var path = require('path');
var multer = require('multer');
var uploader = multer({dest : './Images'});
var fs = require('fs');

// var predictor = require('../predictor/use_keras_model');
var spawn = require("child_process").spawn;

// var PYTHON_ENV = 'G:\\Ananconda\\envs\\tensorflow\\python.exe'
var PYTHON = 'python3'
/* GET home page. */
router.post('/', uploader.single('digitimage'), function(req, res, next) {
    var temp_path = req.file.path;
    var target_path = './Images/' + req.file.originalname;

    fs.rename(temp_path, target_path, function(err){
        var segmentProcess = spawn(PYTHON, [path.resolve("./python_utils/segment.py"), path.resolve(target_path)]);
        segmentProcess.stdout.on('data', function(data){
            console.log("Sending : "+data.toString());
            res.send(data.toString());
        });
        segmentProcess.stderr.on('data', function(data){
            console.log("Error "+data.toString());
            //res.send('Error Occured');
            // res.send(data.toString());            
        });
    });
});

module.exports = router;