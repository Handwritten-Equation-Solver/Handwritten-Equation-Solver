var express = require('express');
var router = express.Router();
var multer = require('multer');
var uploader = multer({dest : './Images'});
var fs = require('fs');

/* GET home page. */
router.post('/', uploader.single('digitimage'), function(req, res, next) {
    var temp_path = req.file.path;
    var target_path = './Images/' + req.file.originalname;

    fs.rename(temp_path, target_path, function(err){
        if(err){
            res.send('Error');
            console.log(err);
        }
        else res.send('Uploaded Successfully');
    });
});

module.exports = router;