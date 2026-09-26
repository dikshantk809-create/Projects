# Giving the rover eyes

The rover ships with no trained model. Until you train one it drives, follows
the row, stops at every plant, photographs it and writes "not checked" — which
is the truth, and better than a confident guess.

This is how you turn those photos into a model that works on **your** plants.

It takes a few evenings spread over a few weeks, because most of the work is
waiting for your plants to show you what problems look like. There is no
shortcut, and downloading someone else's model is not one either: a model
trained on the PlantVillage dataset scores 99% on PlantVillage photos and falls
apart in a real garden, because those photos are single leaves on a plain
background under studio light, and yours are whole plants in soil at four in
the afternoon.

---

## Step 1 — Let the rover collect the photos

Drive it down the row in **Manual** every few days, or set a patrol. Every plant
it stops at gets a photo saved automatically.

Aim for photos across:

- different days (a fortnight at least)
- different light — morning, midday, overcast, late afternoon
- different growth stages
- plants that are **fine** as well as plants that are not. Most of your photos
  should be healthy plants, because most of your plants are healthy

200 photos is a start. 1000 is better. You want at least 100 per problem you
want it to recognise.

---

## Step 2 — Download them and sort them

On the website: **Runs → Download the photo set**.

You get a zip with a folder per label. Almost everything will be in
`_not_sorted_yet`, because nothing has classified them yet.

Now do the part only you can do: **look at every photo and put it in the right
folder.**

```
photos/
  healthy/                    the most common folder, by far
  tomato_early_blight/
  aphid/
  powdery_mildew/
  water_stress/
  ...
```

Rules that matter more than they sound:

- **The folder names must match the keys in `ar750/ai/treatment.py`.** If
  you invent a folder called `blight`, the rover will not know what to do about
  it and will fall back to asking you. Open that file and copy the names.
- **Delete blurry photos.** A blurry photo in `aphid/` teaches the model that
  blur means aphids.
- **If you are not sure what a plant has, do not guess.** Put it in
  `_not_sorted_yet` and leave it out. One wrong label is worth more damage than
  ten missing photos.
- Only keep the labels you actually have enough photos for. A model with four
  labels it knows well beats one with sixteen it half-knows.

---

## Step 3 — Train it

Do this on a laptop, not on the Pi. The Pi can run a model; training one on it
takes days.

Install once:

```bash
pip install tensorflow pillow
```

Save this as `train.py` next to your sorted `photos/` folder:

```python
import tensorflow as tf, pathlib, numpy as np

DATA = pathlib.Path("photos")
SIZE = 224          # must match ai.input_size in config.yaml
BATCH = 16

train = tf.keras.utils.image_dataset_from_directory(
    DATA, validation_split=0.2, subset="training", seed=1,
    image_size=(SIZE, SIZE), batch_size=BATCH)
val = tf.keras.utils.image_dataset_from_directory(
    DATA, validation_split=0.2, subset="validation", seed=1,
    image_size=(SIZE, SIZE), batch_size=BATCH)

names = train.class_names
print("labels:", names)
open("labels.txt", "w").write("\n".join(names) + "\n")

# a rover in a garden sees plants at any angle, in any light
augment = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal"),
    tf.keras.layers.RandomRotation(0.15),
    tf.keras.layers.RandomZoom(0.15),
    tf.keras.layers.RandomBrightness(0.25),
    tf.keras.layers.RandomContrast(0.2),
])

base = tf.keras.applications.MobileNetV2(
    input_shape=(SIZE, SIZE, 3), include_top=False, weights="imagenet")
base.trainable = False

model = tf.keras.Sequential([
    tf.keras.layers.Rescaling(1./127.5, offset=-1),
    augment,
    base,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(len(names), activation="softmax"),
])
model.compile(optimizer="adam",
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])

model.fit(train, validation_data=val, epochs=12)

# then let the top of the pretrained network adjust to your plants too
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False
model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train, validation_data=val, epochs=8)

loss, acc = model.evaluate(val)
print("accuracy on photos it has never seen: %.1f%%" % (acc * 100))

# int8, because that is what runs fast on a Pi
def sample():
    for images, _ in train.take(40):
        for img in images:
            yield [tf.expand_dims(tf.cast(img, tf.float32), 0).numpy()]

conv = tf.lite.TFLiteConverter.from_keras_model(model)
conv.optimizations = [tf.lite.Optimize.DEFAULT]
conv.representative_dataset = sample
conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
conv.inference_input_type = tf.int8
conv.inference_output_type = tf.int8
open("plant_health_int8.tflite", "wb").write(conv.convert())
print("written: plant_health_int8.tflite")
```

```bash
python3 train.py
```

**Read the accuracy number it prints, and be suspicious of it.** That number is
on photos from the same fortnight in the same garden. Real accuracy next month
will be lower.

If it says 99%, something is wrong — usually all the photos of one problem came
from one plant on one day, so the model learned that plant, not that problem.

---

## Step 4 — Put it on the rover

Copy two files into `models/` on the Pi:

```
models/plant_health_int8.tflite
models/labels.txt
```

Install the runtime:

```bash
pip3 install tflite-runtime --break-system-packages
```

Restart it. The chip at the top of the console turns from "no AI model" to
"AI ready".

---

## Step 5 — Do not trust it yet

For the first few weeks, leave **"let it spray on its own" switched off**. The
rover will stop at every problem and ask. Every question is a test: if the
photo it shows you is not what it says it is, you have found a gap in your
training set.

Save those photos, add them to the right folder, and train again. Three rounds
of that is worth more than any amount of fiddling with the training script.

Only turn on automatic spraying once you have gone a full week without
disagreeing with it.

---

## Things that will bite you

**One class swamping the others.** If you have 900 healthy and 40 blight, the
model learns to say "healthy" always and scores 96%. Either collect more
blight, or cut the healthy folder down to about twice your smallest class.

**Photos of the same plant.** Twenty photos of one sick plant is one example,
not twenty. Spread across plants.

**The camera moved.** If you re-mount the camera at a different height or
angle, your old photos no longer match what it sees. Retrain, or put it back.

**Labels that do not match the treatment table.** The model can output whatever
it likes; if the name is not a key in `ar750/ai/treatment.py`, the rover
falls back to "not sure" and asks you. That is the safe failure, but it means
your model appears to do nothing. Check the names match.

**Confidence is not correctness.** A model is confidently wrong all the time.
That is exactly why `ai.auto_spray_confidence` exists, why it cannot be set
below 0.70, and why a virus is never sprayed no matter how sure it is.
