Put your trained model here:

  plant_health_int8.tflite   int8 TFLite, 224 x 224 input
  labels.txt                 one class name per line, in the model's order

The class names must match the keys in ar750/ai/treatment.py, for example:

  healthy
  tomato_early_blight
  tomato_late_blight
  ...

Until these two files exist the rover says "no AI model" on the dashboard and
logs every plant as "not checked", with a photo saved. That is on purpose. It
will not guess a disease it did not see.
