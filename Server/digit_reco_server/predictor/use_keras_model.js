const KerasJS = require('keras-js');
var fs = require('fs');
var PNG = require('pngjs').PNG;

const model = new KerasJS.Model({
    filepaths: {
      model: './keras_model/models_generated/model.json',
      weights: './keras_model/models_generated/model_weights.buf',
      metadata: './keras_model/models_generated/model_metadata.json'
    },
    filesystem: true
  });

function interpret_output(output_arr){
    var maxVal = output_arr[0], predDigit = 0;
    for (var i = 1; i < 10; i++) {
        if (output_arr[i] > maxVal) {
            maxVal = output_arr[i];
            predDigit = i;
        }
    }
    return predDigit;
}

function get_array(image_path, callback){
    arr = new Array();
    fs.createReadStream(image_path)
    .pipe(new PNG({
        filterType: 4
    }))
    .on('parsed', function() {
        console.log('Dimensions = ' + this.height + ' X ' + this.width);
        for (var y = 0; y < this.height; y++) {
            for (var x = 0; x < this.width; x++) {
                var idx = (this.width * y + x) << 2;
                arr[this.width * y + x] = this.data[idx] * 0.2989 + this.data[idx+1] * 0.5870 +
                            this.data[idx+2] * 0.1140;
                arr[this.width * y + x] = arr[this.width * y + x];
            }
        }
        callback(new Float32Array(arr));
    });
}
function make_prediction(image_path, callback) {
    var inp_arr;
    get_array(image_path, function (output) {
        inp_arr = output;
        model.ready()
            .then(() => {
                const inputData = {
                    'input': inp_arr
                }
                return model.predict(inputData)
            })
            .then(outputData => {
                out = interpret_output(outputData['output']);
                callback(out.toString());
            })
            .catch(err => {
                // handle error
            });

    });
}

module.exports = make_prediction;