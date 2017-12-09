var express = require('express');
var router = express.Router();
var path = require('path');
var multer = require('multer');
var uploader = multer({dest : './Images'});
var fs = require('fs');

var predictor = require('../predictor/use_keras_model');

/* GET home page. */
router.post('/', uploader.single('digitimage'), function(req, res, next) {
    var temp_path = req.file.path;
    var target_path = './Images/' + req.file.originalname;

    fs.rename(temp_path, target_path, function(err){
        predictor(target_path, function(result){
            res.send(result);
        });
    });
});

module.exports = router;