# character_extraction

Dependencies: [Jimp](https://github.com/oliver-moran/jimp)

Installation: `npm install --save jimp`

There are two ways of extracting characters:

1. `extractCharacterLocations.getAll()`
2. `extractCharacterLocations.getNearCoord()`


The two methods are wrapped by `main.js`, it is a demo on how `extractCharacterLocations.js` is called.

To run on command line:

`node main.js imageFileOfChoice` or `node main.js imageFileOfChoice xCoordinate yCoordinate`

The current setup will save images of:

1. Full image with locations of bubbles marked
2. Full image with locations of sub-bubbles marked
3. Full image with locations of character locations marked

(Other debug options are controlled in extract/utils/constants.js)

<br/>
  
## Pipeline and Example

![charex_pipeline](https://cloud.githubusercontent.com/assets/7884896/18255404/69203208-7377-11e6-85bd-ddeca5e8f944.PNG)

Blocks in green are the major parts of the current program, the blue part is implemented in `main.js` as an example of using the API

### Example of the pipeline at various stages

[This image](https://cloud.githubusercontent.com/assets/7884896/18254911/0d993610-7371-11e6-96b3-eab3243830b0.jpg) is used for the following demo to find all Chinese character locations. Only the top left bubble will be shown for demoing purposes:

**Find Bubble(s) in image/Find Bubble near given coordinate:**

![bubble_cropped_out](https://cloud.githubusercontent.com/assets/7884896/18255197/ea75eada-7374-11e6-9fd3-4c6545af3831.PNG)

<br/>

**Find Sub-bubbles in Bubbles:**

![subbubble_cropped_out](https://cloud.githubusercontent.com/assets/7884896/18255198/f067ee2a-7374-11e6-866a-38dc771f868d.PNG)

<br/>

**Find Character Locations in Sub-bubbles:**

![charloc_cropped_out](https://cloud.githubusercontent.com/assets/7884896/18255199/f2d15be2-7374-11e6-9e81-3b5aafc2cec8.PNG)

<br/>

### More examples

Examples of the program finding all Character locations in an image (instead of just one Bubble as shown above):

[Example 1](https://cloud.githubusercontent.com/assets/7884896/18255202/014fceec-7375-11e6-8ac9-18dcbd6be936.png)

[Example 2](https://cloud.githubusercontent.com/assets/7884896/18255215/15c5ef6e-7375-11e6-96a1-fa15882c093a.png)

Note that there are false positives when finding Character locations in an image, but that is fine for our purpose

<br/>

### Motivation

A common OCR pipeline:

![ocr_pipeline](https://cloud.githubusercontent.com/assets/7884896/18254879/a508faa4-7370-11e6-9394-991fca7104d3.png)

Since most OCR libraries are not accustomed to text detection and character segmentation of Chinese characters in drawn images, this library is written to deal with those portions

The extracted character locations can be sent to an OCR program that is good at recognizing Chinese characters

<br/>

## Other notes

`character_extraction_prototype.py` is the original prototype used to scope out what algorithms to use to make it accurate and efficient, kept here as a record

Dependencies: [Pillow/PIL](https://python-pillow.github.io/)

To run on command line in debug mode:
`char_extraction.py image.png x_coordinate y_coordinate`

Ex:
`char_extraction.py test.png 734 166`

To run on a full image:
`char_extraction.py image.png`
